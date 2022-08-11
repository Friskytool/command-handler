from discord import Embed
from squid.bot import command, SquidPlugin, CommandContext


class Help(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def help(self, ctx: CommandContext, search: str):
        ...


def setup(bot):
    bot.add_plugin(Help(bot))
