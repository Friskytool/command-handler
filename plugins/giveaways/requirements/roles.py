from squid.bot.context import CommandContext
from squid.errors import ArgumentParsingError
from squid.utils import format_list, s
from ..requirement import Requirement, RequirementPriority, RequirementResponse
from discord import utils
from fuzzywuzzy import process


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
        print(ctx.guild.roles)
        for role_str in argument.split(","):
            role_str = role_str.strip()
            if role_str.startswith("<@&"):
                role_str = role_str[3:-1]
            if role_str.isdigit() and (role := ctx.guild.get_role(int(role_str))):
                roles.append(role.id)
            else:
                result = utils.find(
                    lambda x: x.name.lower() == role_str.lower(), ctx.guild.roles
                )
                if result is not None:
                    roles.append(result.id)
                    continue
                try:
                    name, ra = process.extractOne(
                        role_str, [x.name for x in ctx.guild.roles]
                    )
                except BaseException:
                    pass
                else:
                    if ra >= 60:  # loop?
                        result = utils.get(ctx.guild.roles, name=name)
                        roles.append(result.id)
                        continue
                raise ArgumentParsingError(
                    "Role `{}` not found!".format(role_str),
                )
        return roles  # todo: latr

    def __call__(self, ctx: CommandContext, data: list):
        print(ctx.author.roles)
        for rle in data:  # all roles stored
            if rle not in [i.id for i in ctx.author.roles]:
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
            if rle in [i.id for i in ctx.author.roles]:
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
            if rle in [i.id for i in ctx.author.roles]:
                return RequirementResponse(
                    False,
                    msg=f"You contain the <@&{rle}> role which is blacklisted for this giveaway",
                )
        return RequirementResponse(None)
