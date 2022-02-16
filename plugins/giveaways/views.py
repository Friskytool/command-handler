from squid.models.interaction import InteractionResponse
from squid.models.views import ButtonData, View
from squid.bot import ComponentContext
from discord import Embed
from discord.ui import Button


class GiveawayView(View):
    KEY = "store"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), **k))

    @staticmethod
    def callback(
        ctx: ComponentContext,
        key: str,
    ):
        print(ctx.author.id)
        with ctx.bot.redis as db:
            db.sadd(key, ctx.author.id)
        return InteractionResponse.channel_message(
            embed=Embed(
                description="You have joined the giveaway!",
                color=ctx.bot.colors["secondary"],
            ),
            ephemeral=True,
        )
