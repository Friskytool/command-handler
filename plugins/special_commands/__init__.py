from .plugin import SpecialCommands


def setup(bot):
    bot.add_plugin(SpecialCommands(bot))
