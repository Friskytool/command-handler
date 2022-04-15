from ast import Str
import json
import re
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
from squid.bot.checks import has_role
from discord.ext import commands


class ReminderView(View):
    KEY = "timer-store"

    def __init__(self, *a, key: str = "", cog=None, **k):
        super().__init__(cog=cog)
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
        self.link_re = re.compile(
            r"https:\/\/discord.com\/channels\/(\d*)\/(\d*)\/(\d*)"
        )

    @command(name="timer")
    def timer(self, ctx: CommandContext):
        """Create, Edit, and Delete Timers"""
        ...

    @timer.subcommand(name="start")
    @commands.check(has_role)
    def start(
        self, ctx: CommandContext, *, time: str, title: str = "Timer"
    ) -> InteractionResponse:
        """
        Set a timer for a given time
        """

        if len(time) < 1:
            raise CommandFailed("Invalid time format")

        delta = parse_time(time)

        if delta > timedelta(weeks=8):
            raise CommandFailed(
                "Time too long!\nYou cannot set a timer for more than 8 weeks"
            )

        store_key = uuid.uuid4().hex

        stamp = int((now() + delta).timestamp())

        tkwargs = dict(
            time=f"<t:{stamp}:R>",
            stamp=stamp,
            title=title,
            author=ctx.author.mention,
            channel=ctx.channel.mention,
        )
        message = ctx.send(
            embed=Embed(
                description=ctx.setting("description", **tkwargs),
                timestamp=now() + delta,
            )
            .set_author(name=title, icon_url=ctx.author.avatar.url)
            .set_footer(text="Ends at "),
            view=ReminderView(
                key="timers:{}".format(store_key),
                style=ButtonStyle.primary,
                label="Remind Me",
            ),
        )
        print(message)
        message[
            "link"
        ] = f"https://discord.com/channels/{ctx.guild_id}{ctx.channel_id}/{message['id']}"

        print(ctx.setting("end_message"))
        with ctx.bot.db as db:
            db.timers.insert_one(
                {
                    "host_id": str(ctx.author.id),
                    "message_id": str(message["id"]),
                    "channel_id": str(ctx.channel_id),
                    "guild_id": str(ctx.guild_id),
                    "store_key": store_key,
                    "end": now() + delta,
                    "start": now(),
                    "active": True,
                    "title": title,
                    "icon_url": ctx.author.avatar.url,
                    "end_message": ctx.setting("end_message"),
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
    def list(self, ctx, user=None, channel=None) -> Embed:
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
                raise CommandFailed(f"I cannot find any timers matching those filters")

            print(json.dumps(list(data), indent=3, default=str))
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

                for j in i["timers"]:
                    description += f"[{j['title']}](https://discord.com/channels/{ctx.guild_id}/{i['channel_id']}/{j['message_id']}) - <t:{int(discord_timestamp(j['end']).timestamp())}:R>\n"
                description += "\n"

            embed = Embed(
                title="Timers",
                description=description.strip(),
                color=self.bot.colors["primary"],
            )

            return ctx.respond(embed=embed)

    @timer.subcommand(name="end")
    @commands.check(has_role)
    def end(self, ctx: CommandContext, *, link: str) -> InteractionResponse:
        """
        Stop a timer
        """
        match = self.link_re.match(link)
        if not match:
            raise CommandFailed("Invalid link")

        _, channel_id, message_id = match.groups()

        with ctx.bot.db as db:
            x = db.timers.find_one_and_update(
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
                        description=f"Stopped timer for `{x['title']}`",
                        color=self.bot.colors["primary"],
                    ),
                    ephemeral=True,
                )
            elif x and x["active"]:
                return ctx.respond(
                    embed=Embed(
                        description=f"Timer for `{x['title']}` already ended",
                        color=self.bot.colors["secondary"],
                    ),
                    ephemeral=True,
                )
            else:
                raise CommandFailed("I cannot find that timer")


def setup(bot):
    timers = Timers(bot)
    bot.add_plugin(timers)
    bot.add_handler(ReminderView(cog=timers))
