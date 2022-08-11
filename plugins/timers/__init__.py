from .plugin import Timers
from .views import ReminderView


def setup(bot):
    bot.add_plugin(Timers(bot))
    bot.add_handler(ReminderView)
