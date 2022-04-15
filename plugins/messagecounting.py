from squid.bot import command, SquidPlugin
from discord import Embed

from squid.bot.errors import BotInInput, CommandFailed


class MessageCounting(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def messages(self, ctx, user=None):
        """
        Get's your current messages
        """

        with ctx.bot.db as db:
            user = user or ctx.author

            if user.bot:
                raise BotInInput()

            data = db.messages.find_one(
                {"user_id": user.id, "guild_id": str(ctx.guild_id)}
            )
            if not data:
                if user.id == ctx.author.id:
                    raise CommandFailed("You have no tracked messages yet!")
                else:
                    raise CommandFailed(
                        f'"{user.name}" doesn\'t have any messages yet!'
                    )

            messages = data.get("count", 0)

            return ctx.respond(
                embed=Embed(
                    description=f"*{user.name}* has `{messages:,}` messages",
                    color=self.bot.colors["primary"],
                )
            )


def setup(bot):
    bot.add_plugin(MessageCounting(bot))
