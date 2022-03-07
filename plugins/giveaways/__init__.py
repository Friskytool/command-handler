from .plugin import Giveaways, setup as plugin_setup
from .views import setup as views_setup
from .requirements import setup as requirements_setup


def setup(bot):
    plugin_setup(bot)
    views_setup(bot)
    requirements_setup(bot)
