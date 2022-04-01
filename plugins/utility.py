from discord import Embed
from squid.bot import command, SquidPlugin, CommandContext
import inspect


class Utility(SquidPlugin):  # todo fill in cog
    def __init__(self, bot):
        self.bot = bot

    @command()
    def ping(self, ctx: CommandContext):
        return ctx.respond(
            embed=Embed(description="Pong!", color=self.bot.colors["primary"]),
            ephemeral=True,
        )

    @command()
    def links(self, ctx: CommandContext):
        """Get's the bot's invite links"""

        embed = Embed(
            color=ctx.author.color,
            title="Invite Links",
            description=f"> [Invite link](Bot Invite)](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot%20applications.commands&permissions=1611000937)\n\n> [Invite Link (Support server)](https://discord.gg/TMu242J)\n\n> [Click this link to vote!](https://top.gg/bot/700743797977514004/vote)",
        )

        return ctx.respond(embed=embed)

    @command()
    def about(self, ctx: CommandContext):
        """
        Information about the bot
        Created By:\u200b \u200b[`Squidtoon99`](https://squid.pink) & Frisky\n\u200b
        Premium:\u200b    \u200bhttps://patreon.com/friskytool\n\u200b
        Website:\u200b    \u200bhttps://frisky.dev\n\u200b
        Support Server:\u200b \u200b[discord.gg/TMu242J](https://discord.com/invite/TMu242J)\n\u200b
        """
        return ctx.respond(
            embed=Embed(
                description=inspect.cleandoc(Utility.about.__doc__ or "").strip(),
                color=self.bot.colors["primary"],
            )
        )

    @command()
    def afk(self, ctx, message: str = None):
        with ctx.bot.db as db:
            data = db.AfkStorage.find_one(
                {"id": str(ctx.author.id), "doctype": "user_storage"}
            )
            print(data)
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
