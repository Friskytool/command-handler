from itsdangerous import json
from plugins.giveaways.requirement import RequirementPriority
from squid.models.interaction import InteractionResponse
from squid.models.views import ButtonData, View
from squid.bot import ComponentContext
from discord import Embed
from discord.ui import Button


class GiveawayView(View):
    KEY = "giveaway-store"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), **k))

    @staticmethod
    def callback(
        ctx: ComponentContext,
        key: str,
    ):
        print(key)
        with ctx.bot.redis as redis:

            if raw_data := redis.get(f"db:cache:{key}"):
                data = json.loads(raw_data)
            else:
                with ctx.bot.db as db:
                    data = db.giveaways.find_one({"store_key": key})
                    if data:
                        redis.set(f"db:cache:{key}", json.dumps(data, default=str))
                        redis.expire(f"db:cache:{key}", 60 * 5)  # 5 minutes

        requirements = []
        for name, data in data.get("requirements", {}).items():
            if req := ctx.bot.requirements.get(name, None):
                requirements.append(req)
        print(requirements)
        for requirement in sorted(
            requirements, key=lambda x: x.priority.value, reverse=True
        ):
            response = requirement(ctx, data)
            if response.valid == False:
                return InteractionResponse.channel_message(
                    embed=Embed(
                        title="Missing Requirements",
                        description=response.message,
                        color=ctx.bot.colors["error"],
                    ),
                    ephemeral=True,
                )
            if requirement.priority == RequirementPriority.OVERRIDE and response.valid:
                break

        with ctx.bot.redis as db:
            db.sadd(key, ctx.author.id)
        return InteractionResponse.channel_message(
            embed=Embed(
                description="You have joined the giveaway!",
                color=ctx.bot.colors["secondary"],
            ),
            ephemeral=True,
        )


def setup(bot):
    bot.add_handler(GiveawayView)
