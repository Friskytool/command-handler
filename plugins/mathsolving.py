from discord import Embed
from squid.bot import command, SquidPlugin
import expr


class MathSolving(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def math(self, ctx, expression: str):
        """Evaluate a math expression"""
        result = expr.evaluate(expression, max_safe_number=9e99)

        return ctx.respond(
            embed=Embed(
                description=f"```js\n= {result:,}\n```",
                color=self.bot.colors["primary"],
            ).set_author(name=expression, icon_url=ctx.author.avatar.url)
        )


def setup(bot):
    bot.add_plugin(MathSolving(bot))
