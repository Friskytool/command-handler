from .plugin import Utility


def setup(bot):
    bot.add_plugin(Utility(bot))
