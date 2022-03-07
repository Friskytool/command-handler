from squid.bot.context import CommandContext
from squid.errors import ArgumentParsingError
from squid.utils import format_list, s
from ..requirement import Requirement, RequirementPriority, RequirementResponse


class Role(Requirement):
    name = "required_roles"
    aliases = []
    priority = RequirementPriority.CACHE
    require_member = True
    max = 25

    def display(self, data) -> str:
        print(data)
        return (
            "Required Role" + s(data) + ": " + format_list([f"<@&{i}>" for i in data])
        )

    def convert(self, ctx: CommandContext, argument):
        roles = []
        for role_str in argument.split(","):
            role_str = role_str.strip()
            if not role_str.isdigit() or len(role_str) > 20 or len(role_str) < 16:
                raise ArgumentParsingError("Invalid role ID ({})".format(role_str))
            roles.append(role_str)
        return roles  # todo: latr

    def __call__(self, ctx: CommandContext, data: list):
        for rle in data:  # all roles stored
            if rle not in ctx.author.roles:
                return RequirementResponse(
                    False,
                    msg=f"You don't have the <@&{rle}> role which is required for this giveaway",
                )
        return RequirementResponse(True)


class Bypass(Role):
    name = "bypass_roles"
    priority = RequirementPriority.OVERRIDE

    def display(self, data):
        return super().display(data).replace("Required Role", "Bypass Role")

    def __call__(self, ctx: CommandContext, data: list):
        for rle in data:  # all roles stored
            if rle in ctx.author.roles:
                return RequirementResponse(
                    True,
                )
        return RequirementResponse(None)


class Blacklist(Bypass):
    name = "blacklist_roles"

    def display(self, data):
        return super().display(data).replace("Bypass Role", "Blacklist Role")

    def __call__(self, ctx: CommandContext, data: list):
        for rle in data:
            if rle in ctx.author.roles:
                return RequirementResponse(
                    False,
                    msg=f"You contain the <@&{rle}> role which is blacklisted for this giveaway",
                )
        return RequirementResponse(None)
