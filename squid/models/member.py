from typing import TYPE_CHECKING, Any, List
from discord import member
from discord.utils import parse_time, SnowflakeList


class Member(member.Member):
    if TYPE_CHECKING:
        from squid.bot.state import State

        state: State

    def __init__(self, *, data, guild, state):
        self._state = state
        self._user = state.store_user(data["user"])
        self.guild = guild
        self.joined_at = parse_time(data.get("joined_at"))
        self.premium_since = parse_time(data.get("premium_since"))
        self._roles = SnowflakeList(map(int, data["roles"]))
        self.nick = data.get("nick", None)
