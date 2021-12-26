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

import functions_framework
from flask import abort, jsonify, redirect
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os
from squid.models.interaction import Interaction, ApplicationCommand
from squid.models.enums import InteractionType
from squid.models.functions import lazy, Lazy
from squid.bot import SquidBot
from pymongo import MongoClient


@lazy
def setup_db():
    client = MongoClient(os.getenv("MONGO_URI"))

    if bool(os.getenv("PRODUCTION")):
        db = client.Main
    else:
        db = client.Test
    return db


@SquidBot.from_lazy()
def lazy_bot(cls=SquidBot):
    bot = cls(
        public_key=os.getenv("PUBLIC_KEY"),
        primary_color=0xEA81AE,
        secondary_color=0xEA81AE,
        error_color=0xCC1100,
        squid_db=setup_db,
    )
    import plugins

    plugins.setup(bot)

    @bot.check
    def check_permissions(ctx):
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
        return redirect("https://squid.pink/", code=301)

    if request.method != "POST":
        return abort(405)

    # key verification
    PUBLIC_KEY = os.getenv("PUBLIC_KEY")

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

        if interaction.type == InteractionType.APPLICATION_COMMAND:
            with lazy_bot as bot:
                return bot.process(interaction)
