from copy import copy
from datetime import datetime

from discord import Embed
from squid.bot import SquidPlugin
from squid.bot.checks import has_role
from squid.bot.command import command
from squid.bot.context import CommandContext
from discord.ext import commands

from squid.bot.errors import CommandFailed
from squid.models.interaction import InteractionResponse


class SpecialCommands(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command(name="end event", ignore_register=True)
    def end_event(self, ctx: CommandContext):
        query = {
            "message_id": str(ctx.source.id),
            "channel_id": str(ctx.channel_id),
            "guild_id": str(ctx.guild_id),
        }
        with ctx.bot.db as db:
            obj = db.giveaways.find_one(query)
            typ = "giveaways"

            if not obj:
                obj = db.timers.find_one(query)
                typ = "timers"

        if not obj:
            raise CommandFailed(
                "Cannot find that Event.",
                hint="Make sure you are using this menu on giveaways or timers",
            )

        ctx.command.cog = self.bot.get_plugin(typ)

        has_role(ctx)

        with ctx.bot.redis as redis:
            amn = redis.zscore(typ, obj["store_key"])
            if amn is None:
                raise CommandFailed(f"That {typ[:-1]} has already ended")
            redis.zincrby(typ, -amn, obj["store_key"])

        with ctx.bot.db as db:
            db[typ].find_one_and_update(
                {"_id": obj["_id"]}, {"$set": {"end": datetime.now()}}
            )
        return InteractionResponse.channel_message(
            embed=Embed(
                description=f"Ended {typ.title()}", color=self.bot.colors["primary"]
            ),
            ephemeral=True,
        )
