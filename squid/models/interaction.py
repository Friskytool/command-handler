from typing import TYPE_CHECKING, List, Optional
from discord import AllowedMentions, Embed
from .enums import (
    ApplicationCommandType,
    ApplicationCommandOptionType,
)
from .member import Member
import json
from discord import InteractionType, InteractionResponseType

__all__ = (
    "Interaction",
    "ApplicationCommand",
    "ApplicationCommandOption",
    "InteractionResponse",
)


class Interaction(object):
    def __init__(self, *, data: str, state):
        self._state = state
        self._from_data(data)

    def _from_data(self, data: dict):
        self.id = data["id"]
        self.application_id = data.get("application_id")
        self.type = InteractionType(data["type"])
        self.data = data.get("data")
        self.guild_id = data.get("guild_id")
        self.channel_id = data.get("channel_id")
        self.token = data.get("token")
        self.user = data.get("user")
        self.version = data.get("version")
        self.member = data.get("member")
        self.message = data.get("message")

    def __repr__(self):
        return f"<Interaction id={self.id!r} type={self.type!r}>"


class MessageComponent(object):
    def __init__(self, *, data: dict, state):
        self._state = state
        self._from_data(data)

    def _from_data(self, data: dict):
        self.component_type = data["component_type"]
        self.custom_id = data["custom_id"]

    def __repr__(self):
        return f"<MessageComponent component_type={self.component_type!r} custom_id={self.custom_id!r}>"


class ApplicationCommand(object):
    def __init__(self, *, data: dict, state):
        self._state = state
        self._from_data(data)

    def _from_data(self, data):
        self.guild_id = data.get("guild_id", None)
        self.id = data["id"]
        self.name = data["name"]
        self.type = ApplicationCommandType(data["type"])
        self.resolved = data.get("resolved", None)
        self.options = [
            ApplicationCommandOption(state=self._state, data=option)
            for option in data.get("options", [])
        ]
        self.target_id = data.get("target_id", None)

    @property
    def source(self):
        if self.type == ApplicationCommandType.message:
            return self.resolved["messages"][self.target_id]
        elif self.type == ApplicationCommandType.user:
            return self.resolved["users"][self.target_id]
        else:
            return None

    def __repr__(self):
        return (
            f"<ApplicationCommand id={self.id!r} name={self.name!r} type={self.type!r}>"
        )

    @property
    def guild(self):
        return self._state._get_guild(self.guild_id)


class ApplicationCommandOption(object):
    def __init__(self, *, data: dict, state):
        self._state = state
        self._from_data(data)

    def _from_data(self, data):
        self.name = data["name"]
        self.description = data.get("description", None)
        self.required = data.get("required", False)
        self.type = ApplicationCommandOptionType(data["type"])
        self.value = data.get("value")
        self.min_value = data.get("min_value", None)
        self.max_value = data.get("max_value", None)
        self.options = [
            ApplicationCommandOption(state=self._state, data=option)
            for option in data.get("options", [])
        ]

    def __repr__(self):
        return f"<ApplicationCommandOption name={self.name} type={self.type} value={self.value} options={self.options}>"

    def serialize(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "type": self.type.value,
            "options": [option.serialize() for option in self.options],
        }

        if self.min_value:
            d["min_value"] = self.min_value

        if self.max_value:
            d["max_value"] = self.max_value

        return d


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
    def pong(cls):
        return cls(InteractionResponseType.pong)

    @classmethod
    def channel_message(
        cls,
        content: str = None,
        tts: bool = False,
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
            InteractionResponseType.channel_message,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def deferred_channel_message(
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
            InteractionResponseType.deferred_channel_message,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def defferred_message_update(
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
            InteractionResponseType.deferred_message_update,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    @classmethod
    def message_update(
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
            InteractionResponseType.message_update,
            tts=tts,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            ephemeral=ephemeral,
            components=components,
        )

    def default(self, o):
        if isinstance(o, InteractionResponseType):
            return None

        if isinstance(o, AllowedMentions):
            return o.to_dict()
        return o.__dict__

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
