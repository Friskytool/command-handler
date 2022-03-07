from .roles import Role, Bypass, Blacklist
from .amari import Amari
from .mee6 import Mee6


def setup(bot):
    for req in [Role, Bypass, Blacklist, Amari, Mee6]:
        req.inject(bot)
