from plugins.giveaways.requirement import (
    Requirement,
    RequirementPriority,
    RequirementResponse,
)
from squid.bot.bot import SquidBot
from squid.bot.context import CommandContext, ComponentContext
from squid.errors import ArgumentParsingError
from squid.utils import s


class Amari(Requirement):
    priority = RequirementPriority.API
    name = "amari"
    aliases = ["am", "ari"]

    def __init__(self, bot):
        self.bot: SquidBot = bot
        # self.api: AMARIAPIHANDLER = AMARIAPIHANDLER(bot)

    def display(self, data):
        return f"Amari Level: {str(data[0])}"

    def convert(self, _: CommandContext, argument: int):
        if argument <= 0:
            raise ArgumentParsingError("Amari level must be greater than 0")
        if argument > 1000:
            raise ArgumentParsingError("Amari level must be less than 1000")
        return [argument]

    def fetch_guild_data(self, ctx: CommandContext, guild_id):
        # fetching the guild amari level data
        url = f"https://amaribot.com/api/v1/guild/raw/leaderboard/{guild_id}"
        print("FETCHING AMARI DATA")
        with ctx.bot.session.get(
                url, headers={"Authorization": self.bot.amari_auth}
            ) as req:
            data = req.json()["data"] if req.status_code == 200 else []
        with ctx.bot.redis as redis:
            for d in data:
                redis.set(f"amari:cache:{guild_id}:{d['id']}", d["level"], ex=60 * 10)

    def fetch_user(self, ctx: CommandContext, guild_id, user_id):
        with ctx.bot.redis as redis:
            # redis lookup before api call
            if not redis.exists(f"amari:cache:{guild_id}:{user_id}"):
                self.fetch_guild_data(ctx, guild_id)
            return int(redis.get(f"amari:cache:{guild_id}:{user_id}") or 0)

    def __call__(self, ctx: ComponentContext, data: list):
        data = data[0]
        level = self.fetch_user(ctx, ctx.guild_id, ctx.author.id)
        if level >= data:
            return RequirementResponse(True)
        else:
            return RequirementResponse(
                valid=False,
                msg=f"You need `{data - level}` more amari level{s(data - level)} to enter this giveaway",
            )
