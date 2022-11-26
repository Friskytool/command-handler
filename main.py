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
from inspect import ismethod
import json
import logging
import os

import functions_framework
import sentry_sdk
from flask import abort, jsonify
import requests
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pymongo import MongoClient
from redis import Redis
from sentry_sdk.integrations.gcp import GcpIntegration
import TagScriptEngine as tse

from squid.bot import SquidBot
from squid.bot.errors import CommandFailed
from squid.models.functions import lazy
from squid.models.interaction import Interaction
from squid.settings import Settings

__version__ = "0.0.1"

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[GcpIntegration(timeout_warning=True)],
        attach_stacktrace=True,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )

logging.basicConfig(level=logging.INFO)


@lazy
def setup_db():
    client = MongoClient(os.getenv("MONGO_URL"))

    if bool(os.getenv("PRODUCTION")):
        db = client.Main
    else:
        db = client.Test
    return db


def setup_redis() -> Redis:
    if url := os.getenv("REDIS_URL"):
        k = {}
        if password := os.getenv("REDIS_PASS"):
            k["password"] = password
        redis = Redis.from_url(url, decode_responses=True, **k)
    else:
        redis = Redis()
    return redis


@lazy
def setup_engine():
    blocks = [
        tse.MathBlock(),
        tse.RandomBlock(),
        tse.RangeBlock(),
        tse.AnyBlock(),
        tse.IfBlock(),
        tse.AllBlock(),
        tse.BreakBlock(),
        tse.StrfBlock(),
        tse.StopBlock(),
        tse.AssignmentBlock(),
        tse.FiftyFiftyBlock(),
        tse.ShortCutRedirectBlock("args"),
        tse.LooseVariableGetterBlock(),
        tse.SubstringBlock(),
        tse.EmbedBlock(),
        tse.ReplaceBlock(),
        tse.PythonBlock(),
        tse.URLEncodeBlock(),
        tse.RequireBlock(),
        tse.BlacklistBlock(),
        tse.CommandBlock(),
        tse.OverrideBlock(),
        tse.RedirectBlock(),
        tse.CooldownBlock(),
    ]

    return tse.Interpreter(blocks)


@lazy
def setup_settings():

    # would put this on startup but cold-boot times are kiler
    # req = requests.get(os.getenv("API_URL") + "/static/settings.json")
    with open("./settings.json") as fp:
        data = json.load(fp)

    settings = Settings.from_data(data)

    return settings


@SquidBot.from_lazy()
def lazy_bot(cls=SquidBot):
    bot: SquidBot = cls(
        public_key=os.getenv("PUBLIC_KEY"),
        token=os.getenv("DISCORD_TOKEN"),
        primary_color=0xEA81AE,
        secondary_color=0xEA81AE,
        error_color=0xCC1100,
        redis=setup_redis(),
        squid_db=setup_db,
        squid_engine=setup_engine,
        squid_settings=setup_settings,
        squid_sentry=bool(os.getenv("PRODUCTION")),
        squid_amari_auth=os.getenv("AMARI_AUTH"),
        squid_owner_id=int(os.getenv("OWNER_ID", 0)),
        squid_dashboard_url=os.getenv("dashboard_url", "https://dashboard.squid.pink"),
        squid_application_id=int(os.getenv("APPLICATION_ID", 0)),
        squid_requirements={},
        squid__last_result=None,
    )
    import plugins

    plugins.setup(bot)

    @bot.check
    def check_plugins(ctx):
        with ctx.bot.redis as redis:
            plugins = redis.smembers(f"plugins:{ctx.guild_id}")
            if (
                hasattr(ctx, "command")
                and ctx.command.name != "dummy"
                and not ctx.command.ignore_register
                and ctx.command.cog.qualified_name.lower() not in plugins
            ):
                raise CommandFailed(
                    f"```diff\nMissing Plugin\n- {ctx.command.cog.qualified_name.title()}\n```\n You can enable plugins on the [dashboard]({ctx.bot.dashboard_url}/#/app/{ctx.guild_id}/) \n```",
                    raw=True,
                )

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
        with lazy_bot as bot:
            interaction = Interaction(state=bot.state, data=request.json)
            return bot.process(interaction)
