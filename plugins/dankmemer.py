from discord.user import User
from squid.bot import command, SquidPlugin, CommandContext
from discord import Embed
from fuzzywuzzy import process
from squid.bot.errors import CommandFailed


class DankMemer(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def trades(self, ctx: CommandContext, user=None):
        """View yours or a users trades"""
        with ctx.bot.db as db:
            user = user or ctx.author
            user_id = str(user.id)
            sent = [
                i
                for i in db.dank_memer.aggregate(
                    [
                        {
                            "$match": {
                                "guild_id": str(ctx.guild_id),
                                "sender_id": user_id,
                            }
                        },
                        {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                    ]
                )
            ]

            received = [
                i
                for i in db.dank_memer.aggregate(
                    [
                        {
                            "$match": {
                                "guild_id": str(ctx.guild_id),
                                "receiver_id": user_id,
                            }
                        },
                        {"$group": {"_id": None, "amount": {"$sum": "$amount"}}},
                    ]
                )
            ]

            latest = [
                i
                for i in db.dank_memer.aggregate(
                    [
                        {
                            "$match": {
                                "guild_id": str(ctx.guild_id),
                                "$or": [
                                    {"sender_id": user_id},
                                    {"receiver_id": user_id},
                                ],
                                "timestamp": {"$exists": True},
                            },
                        },
                        {"$sort": {"timestamp": -1}},
                        {"$limit": 5},
                    ]
                )
            ]

            if not sent and not received:
                return ctx.respond(
                    embed=Embed(
                        description="This user has no trades!",
                        color=self.bot.colors["error"],
                    )
                )

            sent = sent[0]["amount"] if sent else 0
            received = received[0]["amount"] if received else 0

            def fmt(rows):
                def inner(row):
                    return f"<@{row['sender_id']}> -> <@{row['receiver_id']}> | {row['amount']}"

                return "\n".join(map(inner, rows))

            return ctx.respond(
                embed=Embed(
                    title=f"{user.name}'s Trades",
                    description="\n".join(
                        [
                            i.strip()
                            for i in f"""
        ```diff
        + received: {received:,}
        - Sent: {sent:,}
        ```
        
        **` RECENT TRADES: `**
        {fmt(latest)}

        """.split(
                                "\n"
                            )
                        ]
                    ),
                    color=self.bot.colors["primary"],
                )
            )


def setup(bot):
    bot.add_plugin(DankMemer(bot))
