from discord.user import User
from squid.bot import command, SquidPlugin, CommandContext
from discord import Embed
from fuzzywuzzy import process
from squid.bot.errors import CommandFailed


class DankMemer(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def dankitem(self, ctx: CommandContext, item: str):
        with ctx.bot.db as db:
            with ctx.bot.redis as redis:
                items = redis.smembers("dank:items")
                print("items: ", items)
                actual_item = process.extractOne(item, items)
                if not actual_item:
                    raise CommandFailed(f"Item `{item}` not found!")

                item_name = redis.get(f"dank:item:{actual_item[0]}:name")
                item_id = actual_item[0]

                item_data = db.dank_memer_trades.aggregate(
                    [
                        {"$match": {"item_id": item_id}},
                        {"$sort": {"date": -1}},
                        {"$limit": 100},
                        {"$group": {"_id": None, "total": {"$avg": "$value"}}},
                        {"$project": {"_id": 0, "total": 1}},
                    ]
                )[0].get("total")

                return ctx.respond(
                    embed=Embed(
                        description=f"{item_name} is worth {item_data:,.2f}",
                        color=self.bot.colors["primary"],
                    )
                )

    @command()
    def trades(self, ctx: CommandContext, user=None):
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

            recieved = [
                i
                for i in db.dank_memer.aggregate(
                    [
                        {
                            "$match": {
                                "guild_id": str(ctx.guild_id),
                                "reciever_id": user_id,
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
                                    {"reciever_id": user_id},
                                ],
                                "timestamp": {"$exists": True},
                            },
                        },
                        {"$sort": {"timestamp": -1}},
                        {"$limit": 5},
                    ]
                )
            ]

            if not sent and not recieved:
                return ctx.respond(
                    embed=Embed(
                        description="This user has no trades!",
                        color=self.bot.colors["error"],
                    )
                )

            sent = sent[0]["amount"] if sent else 0
            recieved = recieved[0]["amount"] if recieved else 0

            def fmt(rows):
                def inner(row):
                    return f"<@{row['sender_id']}> -> <@{row['reciever_id']}> | {row['amount']}"

                return "\n".join(map(inner, rows))

            return ctx.respond(
                embed=Embed(
                    title=f"{user.name}'s Trades",
                    description="\n".join(
                        [
                            i.strip()
                            for i in f"""
        ```diff
        + Recieved: {recieved:,}
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
