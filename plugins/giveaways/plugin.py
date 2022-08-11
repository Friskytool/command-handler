import random
import uuid
from datetime import timedelta
import re
from discord.ext import commands
from discord import AllowedMentions, ButtonStyle, Embed, TextChannel
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.checks import has_role
from squid.bot.errors import CommandFailed
from squid.models.member import Member
from squid.utils import discord_timestamp, display_time, now, parse_time, s
from .views import DonateView, GiveawayView
import bson


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
    @commands.check(has_role)
    def start(
        self,
        ctx: CommandContext,
        # Required
        time: str,
        winners: int,
        prize: str,
        # Optional
        message: str = None,
        donor: Member = None,
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

        if winners > 200:
            raise CommandFailed(
                "Too many winners, contact the developers for a winner limit increase"
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
        print("winners: ", (str(winners)))
        seed = dict(
            time=f"<t:{stamp}:R>",
            stamp=str(stamp),
            unix=str(stamp),
            requirements="\n".join(
                [self.bot.requirements[k].display(v) for k, v in requirements.items()]
            ),
            **requirements,
            prize=prize,
            winners=winners,
            message=message,
            host=ctx.author,
            donor=donor or ctx.author,
            channel=ctx.channel,
            server=ctx.guild,
            guild=ctx.guild,
        )

        data = {}
        items = ["description", "header", "message", "footer", "color"]

        for item in items:
            data[item] = ctx.setting(item, **seed)

        if data.get("color") != "default":
            try:
                data["color"] = int(data["color"].replace("#", ""), base=16)
            except ValueError:
                data["color"] = "default"
        else:
            data["color"] = self.bot.colors["primary"]

        embeds = [
            Embed(
                title=prize,
                description=data["description"],
                timestamp=now() + delta,
                color=data["color"],
            ).set_footer(text=data["footer"])
        ]

        message = ctx.send(
            embeds=embeds,
            view=GiveawayView(
                key=store_key,
                style=ButtonStyle.primary,
                label="Join",
            ),
        )
        if msg := data.get("message"):
            if msg.strip().lower() != "none":
                ctx.send(embed=Embed(description=msg, color=data["color"]))

        with ctx.bot.db as db:
            db.giveaways.insert_one(
                {
                    "host_id": str(ctx.author.id),
                    "message_id": str(message["id"]),
                    "channel_id": str(ctx.channel_id),
                    "guild_id": str(ctx.guild_id),
                    "store_key": store_key,
                    "end": now() + delta,
                    "winners": bson.Int64(winners),
                    "start": now(),
                    "active": True,
                    "prize": prize,
                    "requirements": requirements,
                    "data": {},
                }
            )

        with ctx.bot.redis as redis:
            redis.zincrby("giveaways", stamp, store_key)

        return ctx.respond(
            embed=Embed(
                description=f"Started a giveaway for `{delta}`",
                color=self.bot.colors["primary"],
            ),
            ephemeral=True,
        )

    @giveaway.subcommand(name="end")
    @commands.check(has_role)
    def end(self, ctx: CommandContext, link: str):
        """
        Stop a giveaway
        """
        match = self.link_re.match(link)
        if not match:
            if link.isdigit():
                message_id = str(int(link))
            else:
                with ctx.bot.db as db:
                    if doc := db.giveaways.find_one(
                        {
                            "prize": link,
                            "guild_id": str(ctx.guild_id),
                            "end": {"$gte": now()},
                        }
                    ):
                        message_id = doc["message_id"]
                    else:
                        raise CommandFailed("Invalid link")
        else:
            _, _, message_id = match.groups()

        with ctx.bot.db as db:
            print("id: ", message_id)
            if doc := db.giveaways.find_one_and_update(
                {
                    "guild_id": str(ctx.guild_id),
                    "message_id": str(message_id),
                },
                {"$set": {"end": now()}},
            ):
                key = doc["store_key"]
            else:
                key = None

        if key:
            with ctx.bot.redis as redis:
                print("Key:", key)
                amn = redis.zscore("giveaways", key)
                redis.zincrby("giveaways", -amn, key)

            return ctx.respond(
                embed=Embed(title="Giveaway Ended", color=self.bot.colors["primary"]),
                ephemeral=True,
            )
        else:
            raise CommandFailed("Giveaway not found")

    @giveaway.subcommand(name="reroll")
    @commands.check(has_role)
    def reroll(self, ctx: CommandContext, link: str, amount: int = 1) -> None:
        """Rerolls a giveaway"""
        match = self.link_re.match(link)
        if not match:
            if link.isdigit():
                message_id = str(int(link))
            else:
                with ctx.bot.db as db:
                    if doc := db.giveaways.find_one(
                        {"prize": link, "guild_id": str(ctx.guild_id)}
                    ):
                        message_id = doc["message_id"]
                    else:
                        raise CommandFailed("Invalid link")
        else:
            _, _, message_id = match.groups()

        if amount > 80:
            raise CommandFailed("You cannot reroll more than 80 users at a time")
        with ctx.bot.db as db:
            doc = db.giveaways.find_one({"message_id": message_id}) or {}

            if "users" not in doc:
                raise CommandFailed("Giveaway has no entrants or hasn't ended")

            users = doc.get("users", [])

            random.seed(f'{doc["message_id"]}{self.bot.http.token}')
            random.shuffle(users)

            next_val = doc.get("next_user_seed_input", 0)

            winners = []

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

    @giveaway.subcommand(name="list")
    def list(
        self, ctx, user: Member = None, channel: TextChannel = None, joined: bool = None
    ) -> Embed:
        """
        Get a list of giveaways
        """
        with ctx.bot.db as db:
            match_q = {"guild_id": str(ctx.guild_id), "end": {"$gt": now()}}
            if user:
                match_q["host_id"] = str(user.id)
            if channel:
                match_q["channel_id"] = str(channel.id)

            data = list(
                db.giveaways.aggregate(
                    [
                        {"$match": match_q},
                        {"$sort": {"end": 1}},
                        {"$limit": 50},
                        {
                            "$group": {
                                "_id": "$channel_id",
                                "giveaways": {"$push": "$$ROOT"},
                            }
                        },
                        {"$project": {"_id": 0, "channel_id": "$_id", "giveaways": 1}},
                        {"$limit": 5},
                    ]
                )
            )

            if joined is not None:
                with ctx.bot.redis as redis:
                    for i, chunk in enumerate(data):
                        chunk["giveaways"] = [
                            doc
                            for doc in chunk["giveaways"]
                            if redis.sismember(doc["store_key"], ctx.author.id)
                            == joined
                        ]
                        data[i] = chunk

            if not data:
                raise CommandFailed(
                    f"I cannot find any giveaways matching those filters"
                )

            description = ""
            if channel:
                description += f"In **<#{channel.id}>**"
                if user:
                    description += f" by **{user.mention}**"
            elif user:
                description += f"By **{user.mention}**"

            description += "\n\n"
            for i in data:
                if channel is None:
                    description += f"**<#{i['channel_id']}>**\n"

                for j in i["giveaways"]:
                    description += f"[{j['prize']}](https://discord.com/channels/{ctx.guild_id}/{i['channel_id']}/{j['message_id']}) - <t:{int(discord_timestamp(j['end']).timestamp())}:R>\n"
                description += "\n"

            embed = Embed(
                title="Giveaways",
                description=description.strip(),
                color=self.bot.colors["primary"],
            )

            return ctx.respond(embed=embed)

    @giveaway.subcommand(name="request")
    def request(
        self,
        ctx,
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
        """
        Create a request to sponsor a giveaway. Giveaway managers can choose to accept or deny this request.
        """
        delta = parse_time(time)

        if delta > timedelta(weeks=8):
            raise CommandFailed(
                "Time too long!\nYou cannot set a giveaway for more than 8 weeks"
            )

        if winners < 1:
            raise CommandFailed("You must have at least 1 winner")

        store_key = uuid.uuid4().hex

        stamp = int((now() + delta).timestamp())

        reqs = {
            "required_roles": required_roles,
            "bypass_roles": bypass_roles,
            "blacklist_roles": blacklist_roles,
            "amari": amari,
            "mee6": mee6,
            "booster": booster,
            "danklottery": dank_lottery,
        }

        requirements = {
            v: self.bot.requirements[v].convert(ctx, k) for v, k in reqs.items() if k
        }

        stamp = int((now() + delta).timestamp())

        description = ctx.setting(
            "description",
            time="in " + display_time(delta.total_seconds()),
            stamp=str(stamp),
            requirements="\n".join(
                [self.bot.requirements[k].display(v) for k, v in requirements.items()]
            ),
            **requirements,
            prize=prize,
            winners=winners,
            host=ctx.author,
            donor=ctx.author,
            channel=ctx.channel,
            server=ctx.guild,
            guild=ctx.guild,
        )

        # verify that the output has been configured
        output = ctx.setting("donor_channel")
        if not output:
            raise CommandFailed(
                "Donor channel is not configured",
                hint="You can configure the `donor channel` setting on the [dashboard](https://dashboard.squid.pink)",
            )

        data = {
            "guild_id": str(ctx.guild.id),
            "channel_id": str(ctx.channel.id),
            "donor_id": str(ctx.author.id),
            "delta": time,
            "description": description,
            "prize": prize,
            "winners": int(winners),
            "description": description,
            "requirements": requirements,
            "active": True,
            "store_key": store_key,
            "data": {},
        }

        with ctx.bot.db as db:
            db.donor_queue.insert_one(data)

        return ctx.respond(
            embed=Embed(
                title=prize,
                description=description,
                color=ctx.bot.colors["secondary"],
            )
            .set_author(
                name=f"{ctx.author.name} want's to sponsor a giveaway!",
                icon_url=ctx.author.avatar.url,
            )
            .set_footer(text=f"{int(winners)} winner{s(winners)}"),
            components=DonateView(key=store_key).to_components(),
        )


def setup(bot):
    bot.add_plugin(Giveaways(bot))
    bot.add_handler(GiveawayView)
