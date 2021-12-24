from discord import Embed, user
from squid.bot import command, SquidPlugin
from squid.utils import db_safe
import expr


class InviteCounting(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot

    @command()
    def invites(self, ctx, user: str = None):
        """
        Get's your current invites
        """
        with ctx.bot.db as db:
            user_id = str(user or ctx.author.id)
            y = "You" if user_id == str(ctx.author.id) else "They"
            data = db.invites.find_one(
                {
                    "user_id": user_id,
                    "guild_id": str(ctx.guild_id),
                    "doctype": "user_storage",
                }
            )
            if not data:
                return Embed(
                    description=f"{y} don't have any invites yet!",
                    color=self.bot.colors["error"],
                )

            invites = sum(
                [
                    data.get("regular", 0),
                    data.get("bonus", 0),
                    data.get("fake", 0) * -1,
                    len(data.get("leaves_data")) * -1,
                ]
            )
            return Embed(
                description="\n".join(
                    [
                        i.strip()
                        for i in f"""
        ```diff
        + regular: {data.get('regular',0):,}
        + bonus: {data.get('bonus',0):,}
        - fake: {data.get('fake',0):,}
        - leaves: {len(data.get('leaves_data')):,}
        ```
        """.split(
                            "\n"
                        )
                    ]
                ),
                color=self.bot.colors["primary"],
            ).set_author(name=f"{y} have {invites} invites!")


def setup(bot):
    bot.add_plugin(InviteCounting(bot))
