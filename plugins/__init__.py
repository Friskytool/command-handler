from .fun import Fun, setup as fun_setup
from .invitecounting import InviteCounting, setup as invitecounting_setup
from .mathsolving import MathSolving, setup as mathsolving_setup
from .messagecounting import MessageCounting, setup as messagecounting_setup
from .utility import Utility, setup as utility_setup
from .timers import Timers, setup as timers_setup
from .dankmemer import DankMemer, setup as dankmemer_setup
from .giveaways import Giveaways, setup as giveaways_setup
from .tags import Tags, setup as tags_setup
from .special_commands import SpecialCommands, setup as commands_setup


def setup(bot):
    commands_setup(bot)
    utility_setup(bot)
    mathsolving_setup(bot)
    fun_setup(bot)
    invitecounting_setup(bot)
    messagecounting_setup(bot)
    timers_setup(bot)
    dankmemer_setup(bot)
    giveaways_setup(bot)
    tags_setup(bot)
