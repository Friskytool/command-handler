from discord import ButtonStyle, Color, Embed, InteractionResponse
from squid.bot.context import ComponentContext
from squid.models.views import View, ButtonData
from discord.ui import Button


class ReminderView(View):
    KEY = "timer-store"

    def __init__(self, *a, key: str = "", cog=None, **k):
        super().__init__(cog=cog)
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), **k))

    @staticmethod
    def callback(
        ctx: ComponentContext,
        key: str,
    ):
        with ctx.bot.redis as db:
            db.sadd(key, ctx.author.id)
        return ctx.respond(
            embed=Embed(
                title="Reminder Set",
                description="You will be reminded when the timer ends",
                color=Color.green(),
            ),
            ephemeral=True,
        )


class ManageTimerView(View):
    KEY = "timer-manage"

    def __init__(self, *a, key: str = "", cog=None, **k):
        super().__init__(cog=cog)
        end = ButtonData(self.KEY, key=f"{key}:end")
        cancel = ButtonData(self.KEY, key=f"{key}:cancel")
        self.add_item(
            Button(label="End Timer", custom_id=end.store(), style=ButtonStyle.danger)
        )
        self.add_item(
            Button(
                label="Cancel Timer", style=ButtonStyle.danger, custom_id=cancel.store()
            )
        )

    @staticmethod
    def callback(ctx: ComponentContext, key: str):
        key, action = key.split(":")

        if action == "end":
            ...
        elif action == "cancel":
            ...
