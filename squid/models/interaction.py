from typing import List, Optional
from discord import AllowedMentions, Embed
from .enums import (
    InteractionResponseType,
    InteractionType,
    ApplicationCommandType,
    ApplicationCommandOptionType,
)
from .member import Member, User
import json

__all__ = (
    "Interaction",
    "ApplicationCommand",
    "ApplicationCommandOption",
    "InteractionResponse",
)


class Interaction(object):

    CONSTRUCTORS = {
        InteractionType.PING: "default_constructor",
        InteractionType.APPLICATION_COMMAND: "application_command_constructor",
        InteractionType.MESSAGE_COMPONENT: "message_component_constructor",
        InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE: "application_command_autocomplete_constructor",
    }

    def __init__(
        self,
        *,
        id: str,
        application_id: int,
        type: InteractionType,
        data: dict,
        guild_id: int,
        channel_id: int,
        member: Optional[Member],
        user: User,
        token: str,
        version: str,
        message: Optional[str],
    ):
        self.id = id
        self.application_id = application_id
        self.type = type
        self.data = data
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.member = member
        self.user = user
        self.token = token
        self.version = version
        self.message = message

    def __repr__(self):
        return f"<Interaction id={self.id} application_id={self.application_id} type={self.type} data={self.data} guild_id={self.guild_id} channel_id={self.channel_id} member={self.member} user={self.user} token={self.token} version={self.version} message={self.message}>"

    @classmethod
    def from_json(cls, data):
        typ = InteractionType(data["type"])

        return getattr(
            cls,
            cls.CONSTRUCTORS.get(typ, "default_constructor"),
        )(data)

    @staticmethod
    def _default_constructor(data):
        return dict(
            id=data["id"],
            application_id=data["application_id"],
            type=InteractionType(data["type"]),
            data=data.get("data", {}),
            guild_id=data.get("guild_id", 0),
            channel_id=data.get("channel_id", 0),
            member=(Member.from_json(data["member"]) if data.get("member") else None),
            user=(User.from_json(data["user"]) if data.get("user") else None),
            token=data["token"],
            version=data["version"],
            message=data.get("message"),
        )

    @classmethod
    def default_constructor(cls, data):
        return cls(**cls._default_constructor(data))

    @classmethod
    def application_command_constructor(cls, data):
        default = cls._default_constructor(data)
        default.pop("data")
        return cls(data=ApplicationCommand.from_json(data["data"]), **default)

    @classmethod
    def message_component_constructor(cls, data):
        default = cls._default_constructor(data)
        default.pop("data")
        return cls(data=MessageComponent.from_json(data["data"]), **default)


class MessageComponent(object):
    def __init__(self, *, component_type: int, custom_id: str):
        self.component_type = component_type
        self.custom_id = custom_id

    @classmethod
    def from_json(cls, data):
        return cls(
            component_type=data["component_type"],
            custom_id=data["custom_id"],
        )

    def __repr__(self):
        return f"<MessageComponent component_type={self.component_type} custom_id={self.custom_id}>"


class ApplicationCommand(object):
    def __init__(self, *, id, name, type, resolved=None, options=[]):
        self.id = id
        self.name = name
        self.type = ApplicationCommandType(type)
        self.resolved = resolved
        self.options = [
            ApplicationCommandOption.from_json(option) for option in options
        ]

    def __repr__(self):
        return f"<ApplicationCommand id={self.id} name={self.name} type={self.type} resolved={self.resolved} options={self.options}>"

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class ApplicationCommandOption(object):
    def __init__(self, *, name, type, value, options, focused):
        self.name = name
        self.type = type
        self.value = value
        self.options = options
        self.focused = focused

    def __repr__(self):
        return f"<ApplicationCommandOption name={self.name} type={self.type} value={self.value} options={self.options} focused={self.focused}>"

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data["name"],
            type=ApplicationCommandOptionType(data["type"]),
            value=data.get("value"),
            options=list(map(cls.from_json, data.get("options", []))),
            focused=data.get("focused", False),
        )


class ApplicationCommandOptionChoice(object):
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"<ApplicationCommandOptionChoice name={self.name} value={self.value}>"

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)


class Component(object):
    ...


"""

class InteractionResponseType(Enum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8

"""


class InteractionResponse(object):
    def __init__(
        self,
        type: InteractionResponseType,
        *,
        tts: bool = None,
        content: str = None,
        embed: Embed = None,
        embeds: List[Embed] = [],
        allowed_mentions: AllowedMentions = None,
        ephemeral: bool = False,
        components: List[Component] = [],
        choices: List = [],
    ):
        self.type = type
        self.tts = tts
        self.content = content

        if embed:
            if embeds:
                raise ValueError("Cannot have both embed and embeds")
            embeds = [embed]
        self.embeds = [embed.to_dict() for embed in embeds]

        self.allowed_mentions = allowed_mentions
        self.flags = 1 << 6 if ephemeral else None
        self.components = components

        self.choices = choices

    @classmethod
    def channel_message(
        cls,
        tts: bool = False,
        content: str = None,
        embed: Embed = None,
        embeds: List[Embed] = None,
        allowed_mentions: AllowedMentions = None,
        ephemeral: bool = False,
        components: List[Component] = None,
    ):
        if embeds is None:
            embeds = []
        if components is None:
            components = []
        return cls(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def deferred_channel_message_from_source(
        cls,
        tts: bool = False,
        content: str = None,
        embed: Embed = None,
        embeds: List[Embed] = None,
        allowed_mentions: AllowedMentions = None,
        ephemeral: bool = False,
        components: List[Component] = None,
    ):
        if embeds is None:
            embeds = []
        if components is None:
            components = []
        return cls(
            InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def deferred_update_message(
        cls,
        tts: bool = False,
        content: str = None,
        embed: Embed = None,
        embeds: List[Embed] = None,
        allowed_mentions: AllowedMentions = None,
        ephemeral: bool = False,
        components: List[Component] = None,
    ):
        if embeds is None:
            embeds = []
        if components is None:
            components = []
        return cls(
            InteractionResponseType.DEFERRED_UPDATE_MESSAGE,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def update_message(
        cls,
        tts: bool = False,
        content: str = None,
        embed: Embed = None,
        embeds: List[Embed] = None,
        allowed_mentions: AllowedMentions = None,
        ephemeral: bool = False,
        components: List[Component] = None,
    ):
        if embeds is None:
            embeds = []
        if components is None:
            components = []
        return cls(
            InteractionResponseType.UPDATE_MESSAGE,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def application_command_autocomplete_result(
        cls,
        *,
        choices: List,
    ):
        return cls(
            InteractionResponseType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT,
            choices=choices,
        )

    def default(self, o):
        return None if isinstance(o, InteractionResponseType) else o.__dict__

    def to_dict(self):
        return {
            "type": self.type.value,
            "data": json.loads(
                json.dumps(
                    self,
                    default=self.default,
                    sort_keys=True,
                ),
                object_hook=lambda o: {
                    v: k for v, k in o.items() if k not in [None, [], {}]
                },
            ),
        }
