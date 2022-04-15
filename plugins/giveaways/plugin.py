import random
import uuid
from datetime import timedelta
import re

from discord import AllowedMentions, ButtonStyle, Embed
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.errors import CommandFailed
from squid.utils import now, parse_time, s
from .views import GiveawayView


class Giveaways(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot
        self.link_re = re.compile(
            r"https:\/\/discord.com\/channels\/(\d*)\/(\d*)\/(\d*)"
        )

    @command()
    def giveaway(self, ctx: CommandContext):
        """Create, Manage, and End Giveaways"""
        ...

    @giveaway.subcommand(name="start")
    def start(
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
        booster: bool = None,
        dank_lottery: int = None,
    ):
        """Starts a giveaway"""
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
                "booster": booster,
                "danklottery": dank_lottery,
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
            host=f"<@{ctx.author.id}>",
            donor=f"<@{ctx.author.id}>",
            channel_id=ctx.channel_id,
        )
        message = ctx.send(
            embed=Embed(
                title=prize,
                description=description,
                timestamp=now() + delta,
                color=self.bot.colors["primary"],
            ).set_footer(text=f"{int(winners)} winner{s(winners)} | Ends at "),
            view=GiveawayView(
                key=store_key,
                style=ButtonStyle.secondary,
                label="Join",
            ),
        )

        with ctx.bot.db as db:
            db.giveaways.insert_one(
                {
                    "host_id": str(ctx.author.id),
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

    @giveaway.subcommand(name="end")
    def end(self, ctx: CommandContext, link: str):
        """
        Stop a giveaway
        """
        match = self.link_re.match(link)
        if not match:
            raise CommandFailed("Invalid link")

        _, channel_id, message_id = match.groups()

        with ctx.bot.db as db:
            x = db.giveaways.find_one_and_update(
                {
                    "guild_id": str(ctx.guild_id),
                    "channel_id": str(channel_id),
                    "message_id": str(message_id),
                },
                {"$set": {"end": now()}},
            )

            if x and x["active"]:
                return ctx.respond(
                    embed=Embed(
                        description=f"Stopped giveaway for `{x['prize']}`",
                        color=self.bot.colors["primary"],
                    ),
                    ephemeral=True,
                )
            elif x and x["active"]:
                return ctx.respond(
                    embed=Embed(
                        description=f"giveaway for `{x['prize']}` already ended",
                        color=self.bot.colors["secondary"],
                    ),
                    ephemeral=True,
                )
            else:
                raise CommandFailed("I cannot find that giveaway")

    @giveaway.subcommand(name="reroll")
    def reroll(self, ctx: CommandContext, giveaway_id: str, amount: int = 1) -> None:
        """Rerolls a giveaway"""
        if not giveaway_id.isdigit():
            raise CommandFailed("Invalid giveaway ID")

        with ctx.bot.db as db:
            doc = db.giveaways.find_one({"message_id": giveaway_id})

            if doc["active"]:
                raise CommandFailed("Giveaway is still active")

            elif "users" not in doc:
                raise CommandFailed("Giveaway has no entrants or is still ending")

            users = doc.get("users", [])

            random.seed(f'{doc["message_id"]}{self.bot.http.token}')
            random.shuffle(users)

            next_val = doc.get("next_user_seed_input", 0)

            winners = []
            print(users)

            while users and len(winners) < amount:
                user = users[int(next_val % len(users))]
                next_val += 1

                winners.append(user)

            if next_val != 0:
                db.giveaways.find_one_and_update(
                    {"_id": doc["_id"]},
                    {"$set": {"next_user_seed_input": next_val}},
                )

            if winners:
                winner_str = ", ".join([f"<@{i}>" for i in winners])
            else:
                winner_str = None

            reroll_message = ctx.setting(
                "reroll_message",
                host=f"<@{ctx.author.id}>",
                reroller=ctx.author,
                reroll_channel=ctx.channel,
                server=ctx.guild,
                channel=ctx.channel,
                link=f"https://discordapp.com/channels/{ctx.guild_id}/{doc['channel_id']}/{doc['message_id']}",
                winners=(winner_str or "Nobody"),
                prize=doc["prize"],
            )

        return ctx.respond(
            content=reroll_message, allowed_mentions=AllowedMentions.none()
        )


def setup(bot):
    bot.add_plugin(Giveaways(bot))
    bot.add_handler(GiveawayView)
