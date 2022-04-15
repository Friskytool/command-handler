from squid.bot.context import CommandContext
from ..requirement import Requirement, RequirementPriority, RequirementResponse


class Boost(Requirement):
    name = "booster"
    aliases = []
    priority = RequirementPriority.CACHE
    require_member = True
    max = 1

    def display(self, _data) -> str:
        return "Must be a Server Booster"

    convert = lambda *a: bool(a[-1])

    def __call__(self, ctx: CommandContext, data: list):
        if not ctx.author.premium_since:
            return RequirementResponse(
                False,
                msg=f"You are not a Server Booster and are required to be one to enter this giveaway",
            )
        return RequirementResponse(True)
