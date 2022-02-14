# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os

import functions_framework
import sentry_sdk
from flask import abort, jsonify
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pymongo import MongoClient
from redis import Redis
from sentry_sdk.integrations.gcp import GcpIntegration

from squid.bot import SquidBot
from squid.models.enums import InteractionType
from squid.models.functions import lazy
from squid.models.interaction import Interaction
from squid.models.views import View

__version__ = "0.0.1"

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[GcpIntegration(timeout_warning=True)],
        attach_stacktrace=True,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )

logging.basicConfig(level=logging.DEBUG)


@lazy
def setup_db():
    client = MongoClient(os.getenv("MONGO_URL"))

    if bool(os.getenv("PRODUCTION")):
        db = client.Main
    else:
        db = client.Test
    return db


@lazy
def setup_redis():
    print("Setting up redis")
    if url := os.getenv("REDIS_URL"):
        print(url)
        k = {}
        if password := os.getenv("REDIS_PASS"):
            k["password"] = password
        redis: Redis = Redis.from_url(url, **k)
    else:
        redis: Redis = Redis()
    return redis


@SquidBot.from_lazy()
def lazy_bot(cls=SquidBot):
    bot = cls(
        public_key=os.getenv("PUBLIC_KEY"),
        token=os.getenv("DISCORD_TOKEN"),
        primary_color=0xEA81AE,
        secondary_color=0xEA81AE,
        error_color=0xCC1100,
        squid_db=setup_db,
        squid_redis=setup_redis,
        squid_sentry=bool(os.getenv("PRODUCTION")),
    )
    import plugins

    plugins.setup(bot)

    @bot.check
    def check_plugins(ctx):
        with ctx.bot.redis as redis:
            plugins = redis.smembers(f"plugins:{ctx.guild_id}")
            print(plugins)
            return True

    return bot


@functions_framework.http
def squidbot(request):
    """Responds to a GET request with "Hello world!". Forbids a PUT request.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    if request.method == "GET":
        return "<a href=https://squid.pink/>How'd you get here?</a>", 418

    if request.method != "POST":
        return abort(405)

    # key verification
    PUBLIC_KEY = os.getenv("PUBLIC_KEY") or ""

    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

    signature = request.headers["X-Signature-Ed25519"]
    timestamp = request.headers["X-Signature-Timestamp"]
    body = request.data.decode("utf-8")

    try:
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
    except BadSignatureError:
        return abort(401, "invalid request signature")
    else:
        interaction = Interaction.from_json(request.json)

        if interaction.type == InteractionType.PING:
            return jsonify({"type": 1})

        elif interaction.type in [
            InteractionType.APPLICATION_COMMAND,
            InteractionType.MESSAGE_COMPONENT,
        ]:
            with lazy_bot as bot:
                return bot.process(interaction)
