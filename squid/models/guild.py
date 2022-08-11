from typing import TYPE_CHECKING
from discord import guild, utils
from discord.channel import _channel_factory
from discord.enums import *
from discord.enums import try_enum
from .member import Member
from discord.role import Role


class Guild(guild.Guild):
    if TYPE_CHECKING:
        from squid.bot.state import State

        _state: State

    def __init__(self, *, data: dict, state: "State"):
        self._state = state
        self._from_data(data)

    def _from_data(self, guild):
        member_count = guild.get("member_count", None)
        if member_count is not None:
            self._member_count = member_count

        self.name = guild.get("name")
        # self.region = try_enum(VoiceRegion, guild.get("region"))
        self.verification_level = try_enum(
            VerificationLevel, guild.get("verification_level")
        )
        self.default_notifications = try_enum(
            NotificationLevel, guild.get("default_message_notifications")
        )
        self.explicit_content_filter = try_enum(
            ContentFilter, guild.get("explicit_content_filter", 0)
        )
        self.afk_timeout = guild.get("afk_timeout")
        self._icon = guild.get("icon")
        self._banner = guild.get("banner")
        self.unavailable = guild.get("unavailable", False)
        self.id = int(guild["id"])
        self.mfa_level = guild.get("mfa_level")
        self.features = guild.get("features", [])
        self._splash = guild.get("splash")
        self._system_channel_id = utils._get_as_snowflake(guild, "system_channel_id")
        self.description = guild.get("description")
        self.max_presences = guild.get("max_presences")
        self.max_members = guild.get("max_members")
        self.max_video_channel_users = guild.get("max_video_channel_users")
        self.premium_tier = guild.get("premium_tier", 0)
        self.premium_subscription_count = guild.get("premium_subscription_count") or 0
        self._system_channel_flags = guild.get("system_channel_flags", 0)
        self.preferred_locale = guild.get("preferred_locale")
        self._discovery_splash = guild.get("discovery_splash")
        self._rules_channel_id = utils._get_as_snowflake(guild, "rules_channel_id")
        self._public_updates_channel_id = utils._get_as_snowflake(
            guild, "public_updates_channel_id"
        )
        self._large = None if member_count is None else self._member_count >= 250
        self.owner_id = utils._get_as_snowflake(guild, "owner_id")
        self._afk_channel_id = utils._get_as_snowflake(guild, "afk_channel_id")

    @utils.cached_property
    def _channels(self):
        channels = {}
        for channel_id in self._state._get_all(f"channelmap.guild.{self.id}"):
            channel = self._state._get(f"channel.{channel_id}")
            factory, _ = _channel_factory(channel["type"])
            channels[channel_id] = factory(guild=self, state=self._state, data=channel)
        return channels

    @utils.cached_property
    def _members(self):
        return []
        members = []
        for member in self._state._members_get_all(
            "guild", key_id=self.id, name="member"
        ):
            members.append(Member(guild=self, state=self._state, data=member))
        return members

    @utils.cached_property
    def _roles(self):
        roles = []
        for role in self._state._get_all(f"role.{self.id}"):
            roles.append(
                Role(
                    guild=self,
                    state=self._state,
                    data=self._state._get(f"role.{self.id}.{role}"),
                )
            )
        return roles

    @property
    def channels(self):
        return self._channels.values()

    def get_channel(self, channel_id):
        return self._state._get_guild_channel(channel_id)

    def afk_channel(self):
        channel_id = self._afk_channel_id
        return channel_id and self.get_channel(channel_id)

    def system_channel(self):
        channel_id = self._system_channel_id
        return channel_id and self.get_channel(channel_id)

    def rules_channel(self):
        channel_id = self._rules_channel_id
        return channel_id and self.get_channel(channel_id)

    def public_updates_channel(self):
        channel_id = self._public_updates_channel_id
        return channel_id and self.get_channel(channel_id)

    def members(self):
        return self._members()

    def get_member(self, user_id):
        result = self._state._get(f"member.{self.id}.{user_id}")
        result["user"] = self._state._get(f"user.{user_id}")
        if result:
            result = Member(guild=self, state=self._state, data=result)
        return result

    @property
    def roles(self):
        return self._roles

    def get_role(self, role_id):
        result = self._state._get(f"role.{self.id}.{role_id}")
        if result:
            result = Role(guild=self, state=self._state, data=result)
        return result
