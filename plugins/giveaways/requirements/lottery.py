import expr
from squid.bot.context import CommandContext
from squid.bot.errors import CommandFailed
from squid.errors import ArgumentParsingError
from squid.utils import now, s
from ..requirement import Requirement, RequirementPriority, RequirementResponse


class Lottery(Requirement):
    name = "danklottery"
    aliases = []
    priority = RequirementPriority.MONGO
    require_member = False
    max = 1

    def display(self, data) -> str:
        return f"Must send the host `{data['amount']:,}`"

    def convert(self, ctx: CommandContext, argument: float):
        with ctx.bot.redis as redis:
            if not redis.sismember(f"plugins:{ctx.guild.id}", "dank_memer"):
                raise CommandFailed(
                    f"```diff\nMissing Plugin\n- {'Dank Memer Tracking'}\n```\n You can enable plugins on the [dashboard]({ctx.bot.dashboard_url}/#/app/{ctx.guild_id}/) \n```",
                    raw=True,
                )
        return {
            "amount": int(argument),
            "host_id": ctx.author.id,
            "start": now(),
            "guild_id": ctx.guild.id,
        }

    def __call__(self, ctx: CommandContext, data: list):
        if ctx.author.id == data["host_id"]:
            return RequirementResponse(False, "You can't join your own lottery")

        with ctx.bot.db as db:
            level = [
                i
                for i in db.dank_memer.aggregate(
                    [
                        {
                            "$match": {
                                "guild_id": str(data["guild_id"]),
                                "timestamp": {"$gte": data["start"]},
                                "sender_id": str(ctx.author.id),
                                "receiver_id": str(data["host_id"]),
                            },
                        },
                        {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                    ]
                )
            ]
        if level:
            level = level[0]["amount"]
        level = level or 0

        if level >= data["amount"]:
            return RequirementResponse(True)
        else:
            return RequirementResponse(
                False,
                msg=f"You need to send {data['amount'] - level:,} more coins to enter this giveaway",
            )
