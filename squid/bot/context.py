from typing import TYPE_CHECKING, Callable, Optional, Type
from discord import Role, User, utils
from sentry_sdk.api import capture_exception, push_scope
from squid.bot.errors import SquidError
from squid.models.abc import Messageable
from squid.models.enums import ApplicationCommandOptionType
from squid.models.interaction import (
    ApplicationCommand,
    ApplicationCommandOption,
    InteractionResponse,
)
from squid.models.member import Member
from squid.models.views import ButtonData
from ..models import Interaction

if TYPE_CHECKING:
    from squid.bot import SquidBot
    from squid.http import HttpClient
    from squid.bot.command import SquidCommand
    from squid.bot.plugin import PluginMeta


class SquidContext(Messageable, object):
    def __init__(self, bot, interaction: Interaction):
        self.interaction: Interaction = interaction
        self.bot: "SquidBot" = bot
        self._state = bot.state
        self.http: "HttpClient" = bot.http

        self.interaction_id: int = interaction.id
        self.application_id: int = interaction.application_id
        self.interaction_type = interaction.type
        self.interaction_data = interaction.data

        self.guild_id: str = int(interaction.guild_id)  # casting for rust compat
        self.channel_id = interaction.channel_id

        self._user = {"user": interaction.user, **interaction.member}

        self._token: str = interaction.token
        self._message: str = interaction.message
        self.respond: Callable[...] = InteractionResponse.channel_message

    @property
    def plugin(self) -> "Optional[Type[PluginMeta]]":
        raise NotImplementedError

    @property
    def token(self) -> str:
        return self._token

    @utils.cached_property
    def guild(self):
        if self.guild_id:
            return self.bot.state._get_guild(self.guild_id)
        return None

    @utils.cached_property
    def author(self):
        if self.guild:
            return Member(state=self.bot.state, guild=self.guild, data=self._user)
        return User(state=self.bot.state, data=self._user)

    @utils.cached_property
    def channel(self):
        return self.bot.state._get_guild_channel(self.channel_id)

    # @property
    # def author(self) -> Member:
    #     """Discord will either pass in a user or member object this will return a mix"""

    #     return self.author

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
                    return Member(state=self.bot.state, data={**member, "user": user})
                if member:
                    return Member(state=self.bot.state, data=member)
                return User(state=self.bot.state, data=user)
            elif typ == "channel":
                return resolved.get("channels", {}).get(_id, None)
            else:
                # TODO: Finish up the rest of the types
                for v in resolved.values():  # this is a bit of a hack
                    if data := v.get(_id):
                        return data
            return _id

        return resolver

    # Settings

    @property
    def settings(self) -> dict:
        with self.bot.settings as s:
            return s.settings.get(self.plugin.db_name, {})

    def get_setting(self, name: str):
        return self.settings.get(name)

    def setting(self, name: str, **kw):
        """Gets and parses tagscript in the setting if kwargs is provided

        Args:
            name (str): The name of the setting
        """
        with self.bot.settings as s:
            return s.get(self, name, **kw)


class CommandContext(SquidContext):
    def __init__(self, bot, command: ApplicationCommand, interaction: Interaction):
        super().__init__(bot, interaction)
        self.command_data: ApplicationCommand = command
        self.command: "SquidCommand" = bot._get_command(interaction, command)

    @property
    def plugin(self):
        if self.command:
            return self.command.cog
        else:
            return None

    def _resolve_id(self, typ: str):
        """Given an id we need to pull the data from resolved if present

        Args:
            _id (str): The id to resolve

        Returns:
            str: The resolved id
        """

        def resolver(_id: str):
            resolved = self.command_data.resolved
            print(typ)
            if (
                typ == "user"
            ):  # special case handling where we can pull data from users & members
                member = resolved.get("members", {}).get(_id, None)
                user = resolved.get("users", {}).get(_id, None)
                if member and user:
                    guild = self.bot.state._get_guild(self.guild_id)
                    return Member(
                        state=self.bot.state, guild=guild, data={**member, "user": user}
                    )
                if member:
                    return Member(state=self.bot.state, data=member)

                if not user and (user_obj := self._state.get_user(_id)):
                    return user_obj
                return User(state=self.bot.state, data=user)
            elif typ == "channel":
                return self.bot.state._get_guild_channel(str(_id))
            elif typ == "role":
                if data := resolved.get("roles", {}).get(_id):
                    return Role(
                        state=self.bot.state,
                        guild=self.bot.state._get_guild(self.guild_id),
                        data=data,
                    )
                return self.bot.state._get_role(str(_id))
            else:
                # TODO: Finish up the rest of the types
                for v in resolved.values():  # this is a bit of a hack
                    if data := v.get(_id):
                        return data
            return _id

        return resolver

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
            ApplicationCommandOptionType.string: str,
            ApplicationCommandOptionType.integer: int,
            ApplicationCommandOptionType.boolean: bool,
            ApplicationCommandOptionType.user: self._resolve_id("user"),
            ApplicationCommandOptionType.channel: self._resolve_id("channel"),
            ApplicationCommandOptionType.role: self._resolve_id("role"),
            ApplicationCommandOptionType.mentionable: self._resolve_id(
                "user"
            ),  # TODO: resolve to proper types
            ApplicationCommandOptionType.number: float,
        }

        if i.type in cast and i.value:
            return cast[i.type](i.value)
        return i.value

    @property
    def kwargs(self) -> dict:

        return {
            i.name: self._resolve(i)
            for i in [
                x
                for x in self.command_data.options
                if x.type != ApplicationCommandOptionType.sub_command
                and x.value is not None
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


class ComponentContext(SquidContext):
    def __init__(self, bot, component, interaction):
        super().__init__(bot, interaction)
        self.value = component.custom_id
        self.data: ButtonData = ButtonData.get(self.value)

        self.handler = bot.get_handler(self.data.typ)

    @property
    def plugin(self):
        if self.handler:
            return self.handler.cog
        else:
            return None

    def kwargs(self) -> dict:
        return self.data.data

    def invoke(self, handler, *args, **kwargs):
        return handler.callback(self, *args, **{**self.kwargs(), **kwargs})

    def __repr__(self):
        return f"<ComponentContext: data={self.data} interaction={self.interaction}>"
