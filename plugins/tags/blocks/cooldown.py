from typing import Optional

from TagScriptEngine import Context, Block


class CooldownBlock(Block):
    """
    Redirects the tag response to either the given channel, the author's DMs,
    or uses a reply based on what is passed to the parameter.

    **Usage:** ``{redirect(<"dm"|"reply"|channel>)}``

    **Payload:** None

    **Parameter:** "dm", "reply", channel

    **Examples:** ::

        {redirect(dm)}
        {redirect(reply)}
        {redirect(#general)}
        {redirect(626861902521434160)}
    """

    def will_accept(self, ctx: Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec in ["cd", "cooldown"]

    def process(self, ctx: Context) -> Optional[str]:
        if not ctx.verb.parameter or not ctx.verb.payload:
            return None
        param = ctx.verb.parameter.strip().lower() or "user"
        payload = ctx.verb.payload.lower()
        try:
            payload = int(payload)
        except BaseException:
            return None
        if param not in ["channel", "user", "server"]:
            return None

        ctx.response.actions["cooldown"] = {"bucket": param, "cd": payload}
        return ""
