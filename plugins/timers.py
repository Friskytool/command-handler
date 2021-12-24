from squid.bot import command, SquidPlugin
from squid.bot.errors import CommandFailed
from discord import Embed
from time import time as ctime


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

        unit = time[-1]

        if unit not in ["s", "m", "h", "d"]:
            raise CommandFailed("Invalid time unit (`{}`)".format(unit))

        time = int(time[:-1])

        if unit == "s":
            time = time
        elif unit == "m":
            time = time * 60
        elif unit == "h":
            time = time * 60 * 60
        elif unit == "d":
            time = time * 60 * 60 * 24

        with ctx.bot.db as db:
            db.timers.insert_one(
                {
                    "user_id": ctx.author.id,
                    "guild_id": ctx.guild.id,
                    "end": ctime() + time,
                }
            )

        return Embed(
            description=f"{ctx.author.safe_name} has set a timer for {time} seconds",
            color=self.bot.colors["primary"],
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

            return Embed(
                title="Timers",
                description="\n".join(
                    [
                        f"{user.safe_name} has a timer for {int(end - ctime())} seconds"
                        for end in map(lambda x: x["end"], data)
                    ]
                ),
                color=self.bot.colors["primary"],
            )


def setup(bot):
    bot.add_plugin(Timers(bot))
