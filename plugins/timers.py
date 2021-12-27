from datetime import datetime
from squid.bot import command, SquidPlugin
from squid.bot.errors import CommandFailed
from discord import Embed
from time import time as ctime
import requests
from squid.utils import parse_time


class Timers(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command(name="timer", aliases=["t"])
    def timer(self, ctx, *, time: str) -> Embed:
        """
        Set a timer for a given time
        """

        if len(time) <= 1:
            raise CommandFailed("Invalid time format")

        delta = parse_time(time)

        # with ctx.bot.db as db:
        #     db.timers.insert_one(
        #         {
        #             "user_id": ctx.author.id,
        #             "guild_id": ctx.guild_id,
        #             "end": datetime.now() + delta,
        #             "start": datetime.now(),
        #         }
        #     )
        print(ctx.interaction)
        print(
            f"""
            requests.post(
                f"https://discord.com/api/v9/webhooks/{ctx.application_id}/{ctx.interaction.token}", json={{"content": "test"}}
            ).json()
            """
        )

        return ctx.respond(
            embed=Embed(
                description=f"{ctx.author.safe_name} has set a timer for {int(delta.seconds)} seconds",
                color=self.bot.colors["primary"],
            ),
            ephemeral=True,
        )

    @command(name="timers", aliases=["tlist", "tls"])
    def timers(self, ctx, user=None) -> Embed:
        """
        Get a list of your timers
        """
        with ctx.bot.db as db:
            user = user or ctx.author

            data = db.timers.find({"user_id": user.id, "guild_id": str(ctx.guild.id)})

            if not data:
                raise CommandFailed(
                    f"{'You' if user.id == ctx.author.id else 'They'} don't have any timers"
                )

            return ctx.respond(
                embed=Embed(
                    title="Timers",
                    description="\n".join(
                        [
                            f"{user.safe_name} has a timer for {int(end - ctime())} seconds"
                            for end in map(lambda x: x["end"], data)
                        ]
                    ),
                    color=self.bot.colors["primary"],
                )
            )


def setup(bot):
    bot.add_plugin(Timers(bot))
