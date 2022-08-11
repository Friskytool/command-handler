import functools
from typing import TYPE_CHECKING, Dict, List
from .errors import CheckFailure

if TYPE_CHECKING:
    from .context import CommandContext


def has_role_named(name: str = "roles"):
    return functools.partial(has_role, name=name)


def has_role(ctx: "CommandContext", name: str = "roles"):
    # int casting shouldn't be necessary but better safe
    roles: List[Dict[str, int]] = ctx.setting(name)

    if roles and not any(a.id == b.id for a in ctx.author.roles for b in roles):
        raise CheckFailure(
            "Missing Roles\n" + "\n".join([f"- {i.name}" for i in roles]),
            fmt="diff",
            hint=f"You can edit your `{ctx.plugin.qualified_name.title()} {name.replace('_',' ').title()}` on the **[dashboard](https://dashboard.squid.pink)**",
        )
    return True
