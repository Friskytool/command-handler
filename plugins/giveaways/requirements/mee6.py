from plugins.giveaways.requirement import (
    Requirement,
    RequirementPriority,
    RequirementResponse,
)
from squid.bot.bot import SquidBot
from squid.bot.context import CommandContext, ComponentContext
from squid.errors import ArgumentParsingError
from squid.utils import s


class Mee6(Requirement):
    name = "mee6"

    priority = RequirementPriority.API

    def __init__(self, bot):
        self.bot: SquidBot = bot
        # self.api: AMARIAPIHANDLER = AMARIAPIHANDLER(bot)

    def display(self, data):
        return f"Mee6 Level: {str(data[0])}"

    def convert(self, _: CommandContext, argument: int):
        if argument <= 0:
            raise ArgumentParsingError("Mee6 level must be greater than 0")
        if argument > 1000:
            raise ArgumentParsingError("Mee6 level must be less than 1000")
        return [argument]

    def fetch_guild_data(self, ctx: CommandContext, guild_id):
        # fetching the guild mee6 level data
        url = f"https://mee6.xyz/api/plugins/levels/leaderboard/{guild_id}"

        is_data = True
        page = 0
        data = []
        while is_data:
            with ctx.bot.session.get(url, params={"page": page}) as req:
                if req.status_code == 200:
                    data.extend(req.json()["players"])
                    is_data = len(data) > 0
                else:
                    data = []
                    is_data = False
            page += 1
        with ctx.bot.redis as redis:
            for d in data:
                print(d)
                redis.set(f"mee6:cache:{guild_id}:{d['id']}", d["level"], ex=60 * 10)

    def fetch_user(self, ctx: CommandContext, guild_id, user_id):
        with ctx.bot.redis as redis:
            # redis lookup before api call
            if not redis.exists(f"mee6:cache:{guild_id}:{user_id}"):
                self.fetch_guild_data(ctx, guild_id)
            return int(redis.get(f"mee6:cache:{guild_id}:{user_id}") or 0)

    def __call__(self, ctx: ComponentContext, data: list):
        data = data[0]
        level = self.fetch_user(ctx, ctx.guild_id, ctx.author.id)
        if level >= data:
            return RequirementResponse(True)
        else:
            return RequirementResponse(
                valid=False,
                msg=f"You need `{data - level}` more mee6 level{s(data - level)} to enter this giveaway",
            )
