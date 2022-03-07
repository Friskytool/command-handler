import json
import uuid
from datetime import timedelta
from discord import ButtonStyle, Color, Embed
from discord.ui import Button
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.context import ComponentContext
from squid.bot.errors import CommandFailed
from squid.models.interaction import InteractionResponse
from squid.models.views import ButtonData, View
from squid.utils import discord_timestamp, now, parse_time
from squid.bot.errors import CheckFailure
from discord.ext import commands


def has_role(ctx):
    roles = ctx.setting("roles")
    print("roles:", roles)
    if roles and not any(r["id"] in ctx.author.roles for r in roles):
        raise CheckFailure(
            "Missing Roles\n" + "\n".join([f"- {i['name']}" for i in roles]),
            fmt="diff",
        )
    return True


class ReminderView(View):
    KEY = "timer-store"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), **k))

    @staticmethod
    def callback(
        ctx: ComponentContext,
        key: str,
    ):
        print(ctx.author.id)
        with ctx.bot.redis as db:
            db.sadd(key, ctx.author.id)
        return InteractionResponse.channel_message(
            embed=Embed(
                description="You will be reminded when the timer ends",
                color=Color.green(),
            ),
            ephemeral=True,
        )


class Timers(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command(name="timer")
    def timer(self, ctx: CommandContext):
        ...

    @timer.subcommand(name="start")
    # @commands.check(has_role)
    def start(
        self, ctx: CommandContext, *, time: str, title: str = "Timer"
    ) -> InteractionResponse:
        """
        Set a timer for a given time
        """

        if len(time) <= 1:
            raise CommandFailed("Invalid time format")

        delta = parse_time(time)

        if delta > timedelta(weeks=8):
            raise CommandFailed(
                "Time too long!\nYou cannot set a timer for more than 8 weeks"
            )

        store_key = uuid.uuid4().hex

        stamp = int((now() + delta).timestamp())

        components = None

        message = ctx.send(
            embed=Embed(
                description=ctx.setting("description", time=f"<t:{stamp}:R>"),
                timestamp=now() + delta,
            )
            .set_author(name=title, icon_url=ctx.author.avatar_url)
            .set_footer(text="Ends at ")
            .to_dict(),
            components=ReminderView(
                key="timers:{}".format(store_key),
                style=ButtonStyle.primary,
                label="Remind Me",
            ).to_components(),
        )

        with ctx.bot.db as db:
            db.timers.insert_one(
                {
                    "host_id": ctx.author.id,
                    "message_id": str(message["id"]),
                    "channel_id": str(ctx.channel_id),
                    "guild_id": str(ctx.guild_id),
                    "store_key": store_key,
                    "end": now() + delta,
                    "start": now(),
                    "active": True,
                    "title": title,
                    "icon_url": ctx.author.avatar_url,
                }
            )
        return ctx.respond(
            embed=Embed(
                description=f"Started a timer for `{delta}`",
                color=self.bot.colors["primary"],
            ),
            ephemeral=True,
        )

    @timer.subcommand(name="list")
    def timers(self, ctx, user=None, channel=None) -> Embed:
        """
        Get a list of timers
        """
        with ctx.bot.db as db:
            match_q = {"guild_id": str(ctx.guild_id), "end": {"$gt": now()}}
            if user:
                match_q["host_id"] = str(user.id)
            if channel:
                match_q["channel_id"] = str(channel.id)

            data = list(
                db.timers.aggregate(
                    [
                        {"$match": match_q},
                        {"$sort": {"end": 1}},
                        {"$limit": 50},
                        {
                            "$group": {
                                "_id": "$channel_id",
                                "timers": {"$push": "$$ROOT"},
                            }
                        },
                        {"$project": {"_id": 0, "channel_id": "$_id", "timers": 1}},
                        {"$limit": 5},
                    ]
                )
            )

            if not data:
                raise CommandFailed(
                    f"{'You' if user.id == ctx.author.id else 'They'} don't have any timers"
                )

            print(json.dumps(list(data), indent=3, default=str))
            description = ""
            for i in data:
                description += f"**<#{i['channel_id']}>**\n"
                for j in i["timers"]:
                    description += f"[{j['title']}](https://discord.com/channels/{ctx.guild_id}/{i['channel_id']}/{j['message_id']}) - <t:{int(discord_timestamp(j['end']).timestamp())}:R>\n"
                description += "\n"

            embed = Embed(
                title="Timers",
                description=description.strip(),
                color=self.bot.colors["primary"],
            )

            return ctx.respond(embed=embed)


def setup(bot):
    bot.add_plugin(Timers(bot))
    bot.add_handler(ReminderView)
