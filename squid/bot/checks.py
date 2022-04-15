from typing import TYPE_CHECKING, Dict, List
from .errors import CheckFailure

if TYPE_CHECKING:
    from .context import CommandContext


def has_role(ctx: "CommandContext"):
    # int casting shouldn't be necessary but better safe
    roles: List[Dict[str, int]] = ctx.setting("roles")

    if roles and not any(
        int(r["id"]) in map(lambda o: int(o.id), ctx.author.roles) for r in roles
    ):
        raise CheckFailure(
            "Missing Roles\n" + "\n".join([f"- {i['name']}" for i in roles]),
            fmt="diff",
        )
    return True
