from ast import Str
import json
import re
import uuid
from datetime import timedelta
from discord import ButtonStyle, Color, Embed
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.errors import CommandFailed
from squid.models.interaction import InteractionResponse
from squid.utils import discord_timestamp, now, parse_time
from squid.bot.checks import has_role
from discord.ext import commands
from .views import ReminderView


class Timers(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot
        self.link_re = re.compile(
            r"https:\/\/(?:canary\.)?discord.com\/channels\/(\d*)\/(\d*)\/(\d*)"
        )

    @command(name="timer")
    def timer(self, ctx: CommandContext):
        """Create, Edit, and Delete Timers"""
        ...

    @timer.subcommand(name="start")
    @commands.check(has_role)
    def start(
        self, ctx: CommandContext, time: str, title: str = "Timer"
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
            author=ctx.author,
            channel=ctx.channel,
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
        message[
            "link"
        ] = f"https://discord.com/channels/{ctx.guild_id}{ctx.channel_id}/{message['id']}"

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
                    "end_message": ctx.setting("end_message", **tkwargs),
                }
            )

        with ctx.bot.redis as redis:
            redis.zincrby("timers", stamp, store_key)

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
    def end(self, ctx: CommandContext, link: str) -> InteractionResponse:
        """
        Stop a timer
        """
        match = self.link_re.match(link)
        if not match:
            if link.isdigit():
                message_id = link
            else:
                raise CommandFailed("Invalid link")
        else:
            _, _, message_id = match.groups()

        with ctx.bot.db as db:
            if doc := db.timers.find_one_and_update(
                {
                    "guild_id": str(ctx.guild_id),
                    "message_id": str(message_id),
                },
                {"$set": {"end": now()}},
            ):
                key = doc["store_key"]
            else:
                key = None

        if key is None:
            raise CommandFailed("I cannot find that timer")
        else:
            with ctx.bot.redis as redis:
                amount = redis.zscore("timers", key)
                redis.zincrby("timers", -amount, key)

            return ctx.respond(
                embed=Embed(title="Timer Ended", color=self.bot.colors["primary"]),
                ephemeral=True,
            )

    @timer.subcommand(name="cancel")
    @commands.check(has_role)
    def cancel(self, ctx: CommandContext, link: str) -> InteractionResponse:
        """
        Cancel a timer

        Does the same as `end` but will not ping the users
        """
        match = self.link_re.match(link)
        if not match:
            if link.isdigit():
                message_id = link
            else:
                raise CommandFailed("Invalid link")
        else:
            _, _, message_id = match.groups()

        with ctx.bot.db as db:
            if doc := db.timers.find_one_and_update(
                {
                    "guild_id": str(ctx.guild_id),
                    "message_id": str(message_id),
                },
                {"$set": {"end": now(), "active": False}},
            ):
                key = doc["store_key"]
            else:
                key = None

        if key is None:
            raise CommandFailed("I cannot find that timer")
        else:
            with ctx.bot.redis as redis:
                amount = redis.zscore("timers", key)
                redis.zincrby("timers", -amount, key)

            return ctx.respond(
                embed=Embed(title="Timer Ended", color=self.bot.colors["primary"]),
                ephemeral=True,
            )
