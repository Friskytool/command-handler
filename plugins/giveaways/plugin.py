import uuid
from datetime import timedelta

from discord import ButtonStyle, Color, Embed
from discord.ui import Button
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.context import ComponentContext
from squid.bot.errors import CommandFailed
from squid.utils import now, parse_time, s
from .views import GiveawayView


class Giveaways(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def gstart(
        self,
        ctx: CommandContext,
        # Required
        time: str,
        winners: int,
        prize: str,
        # Optional
        amari: int = 0,
        mee6: int = 0,
        required_roles: str = "",
        bypass_roles: str = "",
        blacklist_roles: str = "",
    ):
        if len(time) <= 1:
            raise CommandFailed("Invalid time format")
        if time.isdigit():
            time += "s"
        delta = parse_time(time)

        if delta > timedelta(weeks=8):
            raise CommandFailed(
                "Time too long!\nYou cannot set a giveaway for more than 8 weeks"
            )

        store_key = uuid.uuid4().hex

        stamp = int((now() + delta).timestamp())

        requirements = {
            v: self.bot.requirements[v].convert(ctx, k)
            for v, k in {
                "required_roles": required_roles,
                "bypass_roles": bypass_roles,
                "blacklist_roles": blacklist_roles,
                "amari": amari,
                "mee6": mee6,
            }.items()
            if k
        }

        description = ctx.setting(
            "description",
            time=f"<t:{stamp}:R>",
            stamp=str(stamp),
            requirements="\n".join(
                [self.bot.requirements[k].display(v) for k, v in requirements.items()]
            ),
            **requirements,
            prize=prize,
            winners=winners,
            host=ctx.author,
            channel_id=ctx.channel_id,
        )
        message = ctx.send(
            embed=Embed(
                title=prize,
                description=description,
                timestamp=now() + delta,
                color=self.bot.colors["primary"],
            )
            .set_footer(text=f"{int(winners)} winner{s(winners)} | Ends at ")
            .to_dict(),
            components=GiveawayView(
                key=store_key,
                style=ButtonStyle.secondary,
                label="Join",
            ).to_components(),
        )

        with ctx.bot.db as db:
            db.giveaways.insert_one(
                {
                    "host_id": ctx.author.id,
                    "message_id": str(message["id"]),
                    "channel_id": str(ctx.channel_id),
                    "guild_id": str(ctx.guild_id),
                    "store_key": store_key,
                    "end": now() + delta,
                    "winners": int(winners),
                    "start": now(),
                    "active": True,
                    "prize": prize,
                    "requirements": requirements,
                    "data": {},
                }
            )

        return ctx.respond(
            embed=Embed(
                description=f"Started a giveaway for `{delta}`",
                color=self.bot.colors["primary"],
            ),
            ephemeral=True,
        )

    @command()
    def gend(self, ctx: CommandContext, giveaway_id: int):
        with ctx.bot.db as db:
            x = db.find_one_and_update(
                {"message_id": giveaway_id}, {"$set": {"end": now()}}
            )
            if x:
                return ctx.respond(
                    embed=Embed(
                        description="Ended the giveaway",
                        color=self.bot.colors["primary"],
                    ),
                    ephemeral=True,
                )
            else:
                return ctx.respond(
                    embed=Embed(
                        description="Could not find giveaway",
                        color=self.bot.colors["error"],
                    ),
                    ephemeral=True,
                )


def setup(bot):
    bot.add_plugin(Giveaways(bot))
    bot.add_handler(GiveawayView)
