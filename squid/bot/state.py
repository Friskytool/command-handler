import inspect
from typing import TYPE_CHECKING, List, Optional
from discord import InteractionType
import orjson
from discord.channel import _channel_factory
from discord.user import BaseUser as User
from discord import state
from squid.models.guild import Guild
from squid.models.interaction import ApplicationCommand, Interaction, MessageComponent


class State(state.ConnectionState):
    if TYPE_CHECKING:
        from squid.bot import SquidBot
        from redis import Redis
        from squid.http.client import HttpClient

        bot: SquidBot
        redis: Redis
        parsers: dict
        http: HttpClient

    def __init__(self, bot, redis, **options):
        self.bot = bot
        self.redis = redis
        self.shard_count = 1
        self.http = bot.http
        self.allowed_mentions = options.get("allowed_mentions")

        self.parsers = {}
        for attr, func in inspect.getmembers(self):
            if attr.startswith("parse_"):
                try:
                    self.parsers[getattr(InteractionType, attr[6:].lower())] = func
                except AttributeError:
                    # only care about interaction events
                    pass

    def execute(self, interaction: Interaction):
        """Trying to mirror dpy a bit here we're going to throw a request from the bot straight into the state to handle it with state built parsers

        Args:
            interaction (Interaction): The interaction to execute
        """
        if interaction.type in self.parsers:
            return self.parsers[interaction.type](interaction)
        else:
            print(f"No parser for {interaction.type}")
            return None

    def parse_ping(self, _interaction: Interaction):
        return self.bot.handle_ping()

    def parse_application_command(self, interaction: Interaction):
        obj = ApplicationCommand(state=self, data=interaction.data)
        return self.bot.handle_application_command(obj, interaction)

    def parse_component(self, interaction: Interaction):
        obj = MessageComponent(state=self, data=interaction.data)
        return self.bot.handle_component(obj, interaction)

    def _get(self, key) -> Optional[dict]:
        result = self.redis.get(str(key))
        if result:
            return orjson.loads(result)
        else:
            return None

    def _get_all(self, key) -> List[dict]:
        result = self.redis.smembers(str(key)) or []
        return [orjson.loads(r) for r in result]

    @property
    def self_id(self):
        u = self._get("user.self")
        return u["id"] if u else None

    def get_user(self, id: int) -> Optional["User"]:
        u = self._get(f"user.{id}")
        if u:
            return User(state=self, data=u)
        return None

    def store_user(self, data: dict):
        user = self.get_user(data["id"])

        if not user:
            user = User(state=self, data=data)
            self.redis.set(f"user.{user.id}", orjson.dumps(data))
        return user

    def _get_guild(self, guild_id):
        result = self._get(f"guild.{guild_id}")
        if result:
            result = Guild(state=self, data=result)
        return result

    def _get_guild_channel(self, channel_id):
        result = self._get(f"channel.{channel_id}")
        if result:
            factory, _ = _channel_factory(result["type"])
            guild = self._get_guild(result["guild_id"])
            if guild:
                result = factory(guild=guild, state=self, data=result)
            else:
                result = None
        return result

    def user(self):
        return self._get("user.self")
