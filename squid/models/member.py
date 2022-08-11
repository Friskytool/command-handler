from typing import TYPE_CHECKING
from discord import member
from discord.utils import parse_time, SnowflakeList
from .abc import Messageable


class Member(Messageable, member.Member):
    if TYPE_CHECKING:
        from squid.bot.state import State

        state: State

    def __init__(self, *, data, guild, state):
        self._state = state
        self.http = state.http
        self._user = state.store_user(data["user"])
        self.guild = guild
        self.joined_at = parse_time(data.get("joined_at"))
        self.premium_since = parse_time(data.get("premium_since"))
        self._roles = SnowflakeList(map(int, data["roles"]))
        self.nick = data.get("nick", None)

    @property
    def channel_id(self):
        return self.http.start_private_message(self.id)["id"]
