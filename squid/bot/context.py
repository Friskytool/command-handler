from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from sentry_sdk.api import capture_exception, push_scope

from squid.bot.errors import SquidError
from squid.models.enums import ApplicationCommandOptionType
from squid.models.functions import Lazy
from squid.models.interaction import (
    ApplicationCommand,
    ApplicationCommandOption,
    InteractionResponse,
)
from squid.models.member import Member, User
from squid.models.views import ButtonData
from ..models import Interaction

if TYPE_CHECKING:
    from squid.bot import SquidBot
    from squid.http import HttpClient
    from squid.bot.command import SquidCommand


class SquidContext(object):
    def __init__(self, bot, interaction: Interaction):
        self.interaction: Interaction = interaction
        self.bot: "SquidBot" = bot
        self.http: "HttpClient" = bot.http

        self.interaction_id: int = interaction.id
        self.application_id: int = interaction.application_id
        self.interaction_type = interaction.type
        self.interaction_data = interaction.data

        self.guild_id: str = str(interaction.guild_id)  # casting for rust compat
        self.channel_id = interaction.channel_id

        self._user = {"user": interaction.user, "member": interaction.member}

        self._token: str = interaction.token
        self._message: str = interaction.message
        self.respond: Callable[...] = InteractionResponse.channel_message

    @property
    def token(self) -> str:
        return self._token

    @property
    def author(self) -> Dict[str, Any]:
        """Discord will either pass in a user or member object this will return a mix"""

        return self._user["member"] or self._user["user"]

    def _resolve_id(self, typ: str):
        """Given an id we need to pull the data from resolved if present

        Args:
            _id (str): The id to resolve

        Returns:
            str: The resolved id
        """

        def resolver(_id: str):
            resolved = self.interaction_data.resolved

            if (
                typ == "user"
            ):  # special case handling where we can pull data from users & members
                member = resolved.get("members", {}).get(_id, None)
                user = resolved.get("users", {}).get(_id, None)
                if member and user:
                    return Member.from_json({**member, "user": user})
                if member:
                    return Member.from_json(member)
                return User.from_json(user)

            else:
                # TODO: Finish up the rest of the types
                for v in resolved.values():  # this is a bit of a hack
                    if data := v.get(_id):
                        return data
            return _id

        return resolver

    def send(self, *a, **k):
        k.setdefault("content", None)
        return self.http.send_message(channel_id=self.channel_id, *a, **k)


class CommandContext(SquidContext):
    def __init__(self, bot, interaction: Interaction):
        super().__init__(bot, interaction)
        self.command: "SquidCommand" = self._get_command(bot, interaction.data)

    def _get_command(self, bot: "SquidBot", cmd: "ApplicationCommand"):
        """Get the actual name of the command including subcommands

        Args:
            interaction (Interaction): The interaction for the command name
        """

        names = [cmd.name]
        s = cmd.options
        for option in s:
            if option.type == ApplicationCommandOptionType.SUB_COMMAND:
                names.append(option.name)
                s.extend(option.options)

        parent = bot
        name = ""
        for i in range(len(names)):
            name = " ".join(names[: i + 1])
            parent = parent.get_command(name)
            if not parent:
                return None
        return parent

    def _resolve(self, i: ApplicationCommandOption):

        """
        STRING	= 3
        INTEGER	= 4	#       Any integer between -2^53 and 2^53
        BOOLEAN	= 5
        USER	= 6
        CHANNEL	= 7	#       Includes all channel types + categories
        ROLE	= 8
        MENTIONABLE	= 9 #   Includes users and roles
        NUMBER	= 10 #      Any double between -2^53 and 2^53
        """
        cast = {
            ApplicationCommandOptionType.STRING: str,
            ApplicationCommandOptionType.INTEGER: int,
            ApplicationCommandOptionType.BOOLEAN: bool,
            ApplicationCommandOptionType.USER: self._resolve_id("user"),
            ApplicationCommandOptionType.CHANNEL: self._resolve_id("channel"),
            ApplicationCommandOptionType.ROLE: self._resolve_id("roles"),
            ApplicationCommandOptionType.MENTIONABLE: self._resolve_id(
                "user"
            ),  # TODO: resolve to proper types
            ApplicationCommandOptionType.NUMBER: float,
        }

        if i.type in cast:
            return cast[i.type](i.value)
        return i.value

    @property
    def kwargs(self) -> dict:

        return {
            i.name: self._resolve(i)
            for i in [
                x
                for x in self.interaction.data.options
                if x.type != ApplicationCommandOptionType.SUB_COMMAND
            ]
        }

    def __repr__(self):
        return f"<CommandContext: {self.interaction!r}>"

    def invoke(self, command, *args, **kwargs):
        try:
            if hasattr(self.bot, "command_check"):
                self.bot.command_check(self, command)
            elif command.parent and hasattr(command.parent, "check"):
                command.parent.command_check(self, command.parent)
            elif hasattr(command, "check"):
                command.command_check(self, command)
            return command(self, *args, **{**self.kwargs, **kwargs})
        except Exception as e:
            with push_scope() as scope:
                scope.set_extra("interaction", self.interaction)
                scope.set_extra("command", command)
                scope.set_extra("args", args)
                scope.set_extra("kwargs", kwargs)

                if self.bot.sentry:
                    capture_exception(e)
                # handling errors
                if hasattr(command, "on_error"):
                    return command.on_error(self, e)
                if command.parent and hasattr(command.parent, "on_error"):
                    return command.parent.on_error(self, e)
                if hasattr(self.bot, "on_error"):
                    return self.bot.on_error(self, e)
                raise SquidError(e)

    # Settings

    @property
    def settings(self) -> dict:
        with self.bot.settings as s:
            return s.settings.get(self.command.cog.db_name, {})

    def get_setting(self, name: str):
        return self.settings.get(name)

    def setting(self, name: str, **kw):
        """Gets and parses tagscript in the setting if kwargs is provided

        Args:
            name (str): The name of the setting
        """
        with self.bot.settings as s:
            return s.get(self, name, **kw)


class ComponentContext(SquidContext):
    def __init__(self, bot, interaction):
        super().__init__(bot, interaction)
        self.value = interaction.data.custom_id
        self.data: ButtonData = ButtonData.get(self.value)

        self.handler = bot.get_handler(self.data.typ)

    def kwargs(self) -> dict:
        return self.data.data

    def invoke(self, handler, *args, **kwargs):
        return handler.callback(self, *args, **{**self.kwargs(), **kwargs})

    def __repr__(self):
        return f"<ComponentContext: data={self.data} interaction={self.interaction}>"
