import json
from plugins.giveaways.requirement import RequirementPriority
from squid.models.interaction import InteractionResponse
from squid.models.views import ButtonData, View
from squid.bot import ComponentContext
from discord import ButtonStyle, Embed
from discord.ui import Button


class ConfirmLeaveView(View):
    KEY = "confirm-leave"

    def __init__(self, *a, key: str, **kw):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(
            Button(
                *a, label="Yes", custom_id=key.store(), style=ButtonStyle.danger, **kw
            )
        )

    @staticmethod
    def callback(ctx: ComponentContext, key: str):

        with ctx.bot.redis as redis:
            if redis.srem(key, ctx.author.id):
                return InteractionResponse.message_update(
                    embed=Embed(
                        title="Left Giveaway",
                        description="You have been removed from this giveaway",
                        color=ctx.bot.colors["primary"],
                    ),
                    components=[],
                    ephemeral=True,
                )
            else:
                return InteractionResponse.message_update(
                    embed=Embed(
                        title="Already Left Giveaway",
                        color=ctx.bot.colors["error"],
                        description="You are not currently entered in this giveaway",
                    ),
                    components=ConfirmLeaveView(key=key, disabled=True).to_components(),
                    ephemeral=True,
                )


class GiveawayView(View):
    KEY = "giveaway-store"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), emoji="🎉", **k))

    @staticmethod
    def callback(
        ctx: ComponentContext,
        key: str,
    ):
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
        for name, data in (data or {}).get("requirements", {}).items():
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
            total = db.scard(key)

            if db.exists(f"cache:{key}:exit:{ctx.author.id}"):
                return InteractionResponse.channel_message(
                    embed=Embed(
                        description="Do you want to leave this giveaway?",
                        color=ctx.bot.colors["secondary"],
                    ).set_footer(
                        text="You can leave giveaways by double-clicking the join button"
                    ),
                    ephemeral=True,
                    components=ConfirmLeaveView(key=key).to_components(),
                )
            else:
                db.set(f"cache:{key}:exit:{ctx.author.id}", 1, ex=5)
        print(GiveawayView(label=total, key=key).to_components())
        return InteractionResponse.message_update(
            components=GiveawayView(label=total, key=key).to_components()
        )


def setup(bot):
    bot.add_handler(GiveawayView)
    bot.add_handler(ConfirmLeaveView)
