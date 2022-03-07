from typing import List
from squid.bot import SquidBot
from squid.bot.context import CommandContext, ComponentContext
from squid.models.member import Member
from enum import Enum


def setup(bot: SquidBot):
    bot.requirements = {}


def _g(cls, **kw):
    return lambda g: kw.get(g, getattr(cls, g, None))


class RequirementResponse:
    def __init__(
        self,
        valid=True,
        msg=None,
    ):
        self.valid = valid  # If they're valid or not
        self.message = msg  # The message to send them

    def __str__(self) -> str:
        return self.msg


class RequirementPriority(Enum):
    """The priority to determine the order of checking requirement information."""

    API = 0  # API-based requirements
    MONGO = 1  # mongo calls
    REDIS = 2  # redis calls
    CACHE = 3  # in-memory cache data / discord data already present
    OVERRIDE = 4  # bypass/overrides


class Requirement(object):
    """
    The base class for all requirements sets up attributes and explanations
    """

    def __new__(cls, bot, name=None, **kw):
        new_cls = super().__new__(cls)
        getter = _g(cls, **kw)
        new_cls.name = (getter("name") or cls.__name__).lower()
        new_cls.bot = bot
        new_cls.description = desc = (getter("description") or "").strip()
        new_cls.short_description = desc.split("\n")[0][:40]
        new_cls.question = getter("question")
        aliases = getter("aliases") or []
        new_cls.max = getter("max") or 1
        new_cls.priority = getter("priority") or RequirementPriority.CACHE
        new_cls.invokes = list(set([new_cls.name, *[i.lower() for i in aliases]]))

        return new_cls

    @classmethod
    def display(self, data) -> List[str]:
        """
        Function that gets called whenever displaying the requirement
        """
        raise NotImplementedError

    @classmethod
    async def convert(self, ctx: CommandContext, argument: str) -> List[object]:
        """
        Parses the input and returns the storage value as a list
        """
        raise NotImplementedError

    @classmethod
    def __check__(cls, ctx: ComponentContext, data: dict) -> RequirementResponse:
        raise NotImplementedError

    @classmethod
    def can_override(cls):
        try:
            return cls.override
        except BaseException:
            return False

    @classmethod
    def inject(cls, bot: SquidBot):
        obj = cls(bot)
        bot.requirements.update({obj.name: obj})
        return obj
