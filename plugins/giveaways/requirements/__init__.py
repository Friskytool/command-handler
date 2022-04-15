from .lottery import Lottery
from .roles import Role, Bypass, Blacklist
from .amari import Amari
from .mee6 import Mee6
from .boost import Boost


def setup(bot):
    for req in [Role, Bypass, Blacklist, Amari, Mee6, Boost, Lottery]:
        req.inject(bot)
