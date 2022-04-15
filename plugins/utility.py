from discord import Embed
import json
from squid.bot import command, SquidPlugin, CommandContext
import inspect

from squid.bot.errors import CommandFailed
from squid.models.commands import CreateApplicationCommand


class Utility(SquidPlugin):  # todo fill in cog
    def __init__(self, bot):
        self.bot = bot

    # @command()
    # def ping(self, ctx: CommandContext):
    #     """Pings the bot"""
    #     return ctx.respond(
    #         embed=Embed(
    #             description=f"Pong!\n",
    #             color=self.bot.colors["primary"],
    #         ),
    #         ephemeral=True,
    #     )

    @command()
    def register(self, ctx: CommandContext, command: str = None, globe: bool = False):
        if ctx.author.id != ctx.bot.owner_id:
            raise CommandFailed("You are not the owner of this bot.")

        commands = ctx.http.get_guild_commands(ctx.bot.application_id, ctx.guild_id)
        commands = {c["id"]: c["name"] for c in commands}

        if not command:
            bot_commands = []
            for plugin in ctx.bot.plugins:
                for cmd in plugin.get_commands():
                    if cmd.name not in commands.values():
                        bot_commands.append(
                            CreateApplicationCommand.from_command(cmd).serialize()
                        )

            c = 0
            for cmd in bot_commands:
                if cmd["name"] == "register":
                    continue
                print(json.dumps(cmd, indent=3))
                ctx.http.upsert_guild_command(ctx.bot.application_id, ctx.guild_id, cmd)
                c += 1

            return ctx.respond(embed=Embed(description=f"Added {c:,} Commands..."))
        else:
            if command := ctx.bot.get_command(command):
                # return ctx.respond(
                #     content="```py\n"
                #     + str(CreateApplicationCommand.from_command(command).serialize())
                #     + "\n```"
                # )
                ctx.http.upsert_guild_command(
                    ctx.bot.application_id,
                    ctx.guild_id,
                    CreateApplicationCommand.from_command(command).serialize(),
                )
                return ctx.respond(content=f"{command.name} upserted.")
            else:
                return ctx.respond(content=f"{command} is not a valid command.")

    @command()
    def links(self, ctx: CommandContext):
        """Get's the bot's invite links"""

        embed = Embed(
            color=ctx.bot.colors["primary"],
            title="Invite Links",
            description=f"> [Invite link](Bot Invite)](https://discord.com/oauth2/authorize?client_id={0}&scope=bot%20applications.commands&permissions=1611000937)\n\n> [Invite Link (Support server)](https://discord.gg/TMu242J)\n\n> [Click this link to vote!](https://top.gg/bot/700743797977514004/vote)",
        )

        return ctx.respond(embed=embed)

    @command()
    def about(self, ctx: CommandContext):
        """
        Information about the bot
        """

        data = """
        Created By:\u200b \u200b[`Squidtoon99`](https://squid.pink) & Frisky\n\u200b
        Premium:\u200b    \u200bhttps://patreon.com/friskytool\n\u200b
        Website:\u200b    \u200bhttps://frisky.dev\n\u200b
        Support Server:\u200b \u200b[discord.gg/TMu242J](https://discord.com/invite/TMu242J)\n\u200b
        """
        return ctx.respond(
            embed=Embed(
                description=inspect.cleandoc(data).strip(),
                color=self.bot.colors["primary"],
            )
        )

    @command()
    def afk(self, ctx, message: str = None):
        with ctx.bot.db as db:
            data = db.AfkStorage.find_one(
                {"id": str(ctx.author.id), "doctype": "user_storage"}
            )
            if not data or message:
                message = message or "I'm AFK"
                db.AfkStorage.find_one_and_update(
                    {"id": str(ctx.author.id), "doctype": "user_storage"},
                    {
                        "$set": {
                            "message": message,
                            "guild": {"id": str(ctx.guild_id)},
                        }
                    },
                    upsert=True,
                )

                return ctx.respond(
                    embed=Embed(
                        color=ctx.bot.colors["primary"],
                        title="Set AFK",
                        description=f"I set your afk to `{message}`",
                    )
                )
            db.AfkStorage.find_one_and_delete(
                {"id": str(ctx.author.id), "doctype": "user_storage"}
            )

            return ctx.respond(
                embed=Embed(
                    color=ctx.bot.colors["secondary"],
                    title="Removed AFK",
                    description="I removed your afk",
                )
            )


def setup(bot):
    bot.add_plugin(Utility(bot))
