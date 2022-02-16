from .plugin import Giveaways


def setup(bot):
    bot.add_plugin(Giveaways(bot))
