from squid.bot.errors import SquidError
from squid.models.enums import ApplicationCommandOptionType
from squid.models.functions import Lazy
from squid.models.interaction import ApplicationCommandOption
from squid.models.member import Member, User
from ..models import Interaction


class SquidContext(object):
    def __init__(self, bot, interaction: Interaction):
        self.interaction = interaction
        self.bot = bot

        self.command = bot.get_command(interaction.data.name)

        self.interaction_id = interaction.id
        self.application_id = interaction.application_id
        self.interaction_type = interaction.type
        self.interaction_data = interaction.data

        self.guild_id = interaction.guild_id
        self.channel_id = interaction.channel_id

        self._user = {"user": interaction.user, "member": interaction.member}

        self._token = interaction.token
        self._message = interaction.message

    @property
    def token(self):
        return self._token

    @property
    def author(self):
        """Discord will either pass in a user or member object this will return a mix"""

        if self._user["member"]:
            return self._user["member"]
        return self._user["user"]

    # you should probably never do this
    def __getattribute__(self, name: str):
        obj = object.__getattribute__(self, name)
        if isinstance(obj, Lazy):
            with obj:
                return obj
        return obj

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
        return {i.name: self._resolve(i) for i in self.interaction.data.options}

    def __repr__(self):
        return "<SquidContext: {}>".format(self.interaction)

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
            # handling errors
            if hasattr(command, "on_error"):
                return command.on_error(self, e)
            if command.parent and hasattr(command.parent, "on_error"):
                return command.parent.on_error(self, e)
            if hasattr(self.bot, "on_error"):
                return self.bot.on_error(self, e)
            raise SquidError(e)

    def send(self, *a, **k):
        with self.bot.webhook(self.application_id, self.token) as hook:
            return hook.send(*a, **k)
