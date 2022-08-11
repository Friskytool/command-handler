from datetime import datetime
import json
from plugins.giveaways.requirement import RequirementPriority
from squid.models.abc import Messageable
from squid.models.interaction import InteractionResponse
from squid.models.views import ButtonData, View
from squid.bot import ComponentContext
from squid.bot.checks import has_role
from discord import ButtonStyle, Embed
from discord.ui import Button

from squid.utils import display_time, now, parse_time, s


class C(Messageable):
    def __init__(self, *, state, http, channel_id):
        self._state = state
        self.http = http
        self.channel_id = channel_id


class ManageEntryView(View):
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
                    components=ManageEntryView(key=key, disabled=True).to_components(),
                    ephemeral=True,
                )
            else:
                return InteractionResponse.message_update(
                    embed=Embed(
                        title="Already Left Giveaway",
                        color=ctx.bot.colors["error"],
                        description="You are not currently entered in this giveaway",
                    ),
                    components=ManageEntryView(key=key, disabled=True).to_components(),
                    ephemeral=True,
                )


class GiveawayView(View):
    KEY = "giveaway-store"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        k.setdefault("style", ButtonStyle.primary)
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
                    components=ManageEntryView(key=key).to_components(),
                )
            else:
                db.set(f"cache:{key}:exit:{ctx.author.id}", 1, ex=5)

        return InteractionResponse.message_update(
            components=GiveawayView(label=total, key=key).to_components()
        )


class DonateView(View):
    KEY = "donate-store"

    def __init__(self, *a, key: str, **kw):
        super().__init__()
        accept = ButtonData(self.KEY, key=key, deny=False)
        deny = ButtonData(self.KEY, key=key, deny=True)
        if "selected" in kw:
            selected = kw.pop("selected")
            kw["disabled"] = True
        else:
            selected = None
        self.add_item(
            Button(
                *a,
                label="Accept",
                custom_id=accept.store(),
                style=ButtonStyle.success
                if selected is None or selected == "accept"
                else ButtonStyle.gray,
                **kw,
            )
        )
        self.add_item(
            Button(
                *a,
                label="Deny",
                custom_id=deny.store(),
                style=ButtonStyle.danger
                if selected is None or selected == "deny"
                else ButtonStyle.gray,
                **kw,
            )
        )

    @staticmethod
    def callback(ctx: ComponentContext, key: str, deny: bool):
        ctx.handler.cog = ctx.bot.get_plugin("giveaways")
        has_role(ctx)

        donor_channel = ctx.setting("donor_channel")
        donor_channel = C(
            state=ctx.bot.state, http=ctx.bot.http, channel_id=donor_channel.id
        )
        with ctx.bot.db as db:
            doc = db.donor_queue.find_one_and_delete({"store_key": key})
        if not doc:
            return InteractionResponse.message_update(
                components=DonateView(
                    key=key, disabled=True, selected=""
                ).to_components(),
            )

        if deny:
            if donor := ctx.guild.get_member(int(doc["donor_id"])):
                donor.send(
                    embed=Embed(
                        title="Donation Denied",
                        description=f"Your donation for `{doc['prize']}` has been denied by {ctx.author.mention} ({ctx.author.id})",
                    )
                )
        else:
            # creating the gaw
            donor = ctx.guild.get_member(int(doc["donor_id"]))
            doc["delta"] = parse_time(doc["delta"])
            doc["start"] = now()
            doc["end"] = now() + doc["delta"]
            doc["host_id"] = str(ctx.author.id)
            doc["channel_id"] = str(donor_channel.channel_id)
            stamp = int((now() + doc["delta"]).timestamp())

            description = ctx.setting(
                "description",
                time=f"<t:{stamp}:R>",
                stamp=str(stamp),
                requirements="\n".join(
                    [
                        ctx.bot.requirements[k].display(v)
                        for k, v in doc["requirements"].items()
                    ]
                ),
                **doc["requirements"],
                prize=doc["prize"],
                winners=doc["winners"],
                host=ctx.author,
                donor=donor,
                channel=donor_channel,
                server=ctx.guild,
                guild=ctx.guild,
            )

            message = donor_channel.send(
                embed=Embed(
                    title=doc["prize"],
                    description=description,
                    timestamp=doc["end"],
                    color=ctx.bot.colors["primary"],
                ).set_footer(
                    text=f"{int(doc['winners'])} winner{s(doc['winners'])} | Ends at "
                ),
                view=GiveawayView(
                    key=doc["store_key"],
                    style=ButtonStyle.primary,
                    label="Join",
                ),
            )

            doc["message_id"] = str(message["id"])
            doc.pop("delta")
            with ctx.bot.db as db:
                db.giveaways.insert_one(doc)

            with ctx.bot.redis as redis:
                redis.zincrby("giveaways", stamp, doc["store_key"])

        return InteractionResponse.message_update(
            components=DonateView(
                key=key, disabled=True, selected="deny" if deny else "accept"
            ).to_components(),
        )


def setup(bot):
    bot.add_handler(GiveawayView)
    bot.add_handler(ManageEntryView)
    bot.add_handler(DonateView)
