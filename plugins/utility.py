from discord import Embed
from squid.bot import command
from squid.plugin import SquidPlugin


class Utility(SquidPlugin):  # todo fill in cog
    def __init__(self, bot):
        self.bot = bot

    @command()
    def ping(self, ctx):
        return Embed(title="Pong!", description="It works!", color=0x00FF00)


def setup(bot):
    bot.add_plugin(Utility(bot))
