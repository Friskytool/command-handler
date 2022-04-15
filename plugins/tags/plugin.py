from typing import TYPE_CHECKING, Dict
import discord
from discord import utils
from squid.bot import CommandContext, SquidPlugin, command
from squid.bot.errors import CheckFailure, RequireCheckFailure
from squid.models.commands import CreateApplicationCommand
from squid.models.enums import ApplicationCommandOptionType, ApplicationCommandType
from squid.models.interaction import (
    ApplicationCommand,
    ApplicationCommandOption,
    Interaction,
)
from squid.models.tags import Tag, TagArgument
import TagScriptEngine as tse
from .blocks import stable_blocks
from fuzzywuzzy import process
from copy import copy


class Tags(SquidPlugin):
    def __init__(self, bot):
        self.bot = bot
        self._og_get = copy(bot._get_command)
        bot._get_command = self.get_command

        blocks = stable_blocks + [
            tse.MathBlock(),
            tse.RandomBlock(),
            tse.RangeBlock(),
            tse.AnyBlock(),
            tse.IfBlock(),
            tse.AllBlock(),
            tse.BreakBlock(),
            tse.StrfBlock(),
            tse.StopBlock(),
            tse.AssignmentBlock(),
            tse.FiftyFiftyBlock(),
            tse.ShortCutRedirectBlock("args"),
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.URLEncodeBlock(),
            # tse.JoinBlock(),
        ]

        self.engine = tse.Interpreter(blocks=blocks)

    @staticmethod
    def proper_cast(v: ApplicationCommandOptionType, k):
        return {
            ApplicationCommandOptionType.string: tse.StringAdapter,
            ApplicationCommandOptionType.integer: tse.IntAdapter,
            ApplicationCommandOptionType.number: tse.IntAdapter,
            ApplicationCommandOptionType.boolean: lambda o: tse.StringAdapter(str(o)),
            ApplicationCommandOptionType.user: tse.MemberAdapter,
            ApplicationCommandOptionType.role: tse.AttributeAdapter,
            ApplicationCommandOptionType.channel: tse.ChannelAdapter,
            ApplicationCommandOptionType.mentionable: tse.AttributeAdapter,
        }[v](k)

    def cog_unload(self):
        self.bot._get_command = self._og_get

    def get_tag(self, name: str, guild_id: int):
        with self.bot.db as db:
            if data := db.tags.find_one(dict(name=name, guild_id=str(guild_id))):
                return Tag(state=self.bot.state, data=data)
        return None

    def get_command(self, interaction: "Interaction", cmd: "ApplicationCommand"):
        """Get the actual name of the command including subcommands

        Args:
            interaction (Interaction): The interaction for the command name
        """

        if command := self._og_get(interaction, cmd):
            return command

        if tag := self.get_tag(cmd.name, guild_id=interaction.guild_id):
            print(tag)
            return self._handle_tag(tag)

        return None

    def _handle_tag(self, tag: Tag):
        @command(name="dummy")
        def handler(ctx: CommandContext, **kw):
            return self.handle_tag(ctx, tag, data=kw)

        return handler

    def handle_tag(
        self, ctx: CommandContext, tag: Tag, data: Dict[str, TagArgument] = None, **kw
    ):
        print(data.values())
        seed = {
            "author": self.proper_cast(ApplicationCommandOptionType.user, ctx.author),
            "channel": self.proper_cast(
                ApplicationCommandOptionType.channel, ctx.channel
            ),
            "guild": tse.AttributeAdapter(ctx.guild),
            **{
                v: self.proper_cast(opt.type, k)
                for opt, (v, k) in zip(tag.options, data.items())
            },
        }

        if "target" not in seed:
            seed["target"] = seed["author"]

        output = tag.run(self.engine, seed_variables=seed, **kw)

        # tag.update_last_used()
        content = output.body[:2000] if output.body else None
        actions = output.actions
        embeds = []
        hidden = False
        if embed := actions.get("embed"):
            embeds.append(embed)
        destination = ctx

        if actions:
            try:
                self.validate_checks(ctx, actions, tag)
            except CheckFailure as error:
                response = error.message
                if response is not None:
                    if response.strip():
                        return ctx.respond(content=response[:2000], ephemeral=True)
                else:
                    ctx.response(content="❌", ephemeral=True)
                return

            if actions.get("commands"):

                for command in actions["commands"]:
                    if command.startswith("tag") or command == "invoketag":

                        return ctx.respond(
                            content="Tag Looping is not allowed", ephemeral=True
                        )
                    parts = command.split(" ")
                    name = []
                    while parts and ":" not in parts[0]:
                        name.append(parts.pop(0))
                    args = {}
                    arg_name = ""
                    arg_values = []
                    while parts:
                        if parts[0].endswith(":"):
                            if arg_values:
                                args[arg_name] = " ".join(arg_values)
                                arg_name = ""
                                arg_values = []
                            arg_name = parts.pop(0)[:-1]
                        else:
                            if not arg_name:
                                return ctx.respond(
                                    "Tag command arguments must be in the format <name>: <argument>",
                                    ephemeral=True,
                                )
                            arg_values.append(parts.pop(0))
                    if arg_name and arg_values:
                        args[arg_name] = " ".join(arg_values)
                    if TYPE_CHECKING:
                        from squid.bot.command import SquidCommand
                    to_invoke: "SquidCommand" = self._og_get(None, None, names=name)
                    print(to_invoke)
                    builder = CreateApplicationCommand.from_command(to_invoke)
                    base_options = builder.options
                    for option in base_options:
                        if v := args.get(option.name):
                            option.value = v
                    cmd = copy(ctx.command_data)
                    cmd.options = base_options
                    cmd.name = name[0]

                    new_ctx = copy(ctx)
                    new_ctx.command_data = cmd
                    new_ctx.command = to_invoke
                    resp = to_invoke.invoke(new_ctx)

                    embeds.extend([discord.Embed.from_dict(i) for i in resp.embeds])
                    hidden = hidden or resp.flags == 1 << 6
            # if target := actions.get("target"):
            #     if target == "dm": #TODO: finish target
            #         destination = ctx.author.create_dm()
            #     elif target == "reply":
            #         pass
            #     else:
            #         try:

            #         except commands.BadArgument:
            #             pass
            #         else:
            #             if chan.permissions_for(ctx.guild.me).send_messages:
            #                 destination = chan

        msg = None
        extras = {}
        if not content and not embeds:
            content = "```xml\n< Tag recieved >\n```"
            hidden = True

        return ctx.respond(
            content=content,
            embeds=embeds,
            ephemeral=((destination == ctx) and hidden) or actions.get("hidden", False),
            allowed_mentions=discord.AllowedMentions(
                users=True, everyone=False, roles=False, replied_user=True
            ),
            **extras,
        )
        # if msg and (react := actions.get("react")): TODO: figure out post-send reactions
        #     to_gather.append(self.do_reactions(ctx, react, msg))
        # if command_messages:
        #     silent = actions.get("silent", False)
        #     overrides = actions.get("overrides")
        #     to_gather.append(self.process_commands(command_messages, silent, overrides))

        # if to_gather:
        #     for i in to_gather:
        #         i() # made sync

    def validate_checks(self, ctx: CommandContext, actions: dict, tag: Tag):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(lambda _: self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(lambda _: self.validate_blacklist(ctx, blacklist))
        if cooldown := actions.get("cooldown"):
            to_gather.append(lambda _: self.validate_cooldown(ctx, cooldown, tag))

        for i in to_gather:
            if not i(""):
                return False

    def validate_cooldown(self, ctx: CommandContext, cooldown, tag: Tag):
        with self.bot.redis as redis:
            bucket_type = cooldown.get("bucket", "user")

            if bucket_type == "channel":
                bucket = ctx.channel_id
            elif bucket_type == "user":
                bucket = ctx.author.id
            elif bucket_type == "server":
                bucket = ctx.guild_id

            k = f"Cooldown.{ctx.guild_id}:tag:{tag.name}:cooldown:{bucket}"
            t = redis.ttl(k)

            if t > 0:
                if t > cooldown.get("cd"):
                    t = cooldown.get("cd")
                    redis.expire(k, t)  # updated cooldown
                raise CheckFailure(
                    f"`Cooldown` You cannot run this command for another {t:,} seconds"
                )
            elif t == -2:
                redis.set(
                    k, "cooldown", ex=max([cooldown.get("cd"), 86400 * 7])
                )  # a week

    def validate_requires(self, ctx: CommandContext, requires: dict):
        default_output = "Missing Roles/Channels\n"
        r, c = [], []
        for argument in requires["items"]:
            role_or_channel = self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                r.append(role_or_channel.name)
                if role_or_channel in ctx.author.roles:
                    return
            else:
                if role_or_channel == ctx.channel:
                    return
                c.append(role_or_channel.name)
        n = "\n"
        if r:
            default_output += f"Roles: \n- {n + ' -'.join(r)}\n"
        if c:
            default_output += f"Channels: \n- {(n+ ' -').join(c)}\n"
        raise RequireCheckFailure(requires["response"] or default_output)

    def validate_blacklist(self, ctx: CommandContext, blacklist: dict):
        r, c = [], []
        for argument in blacklist["items"]:
            role_or_channel = self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    raise RequireCheckFailure(
                        blacklist["response"]
                        or "Blacklisted Role\n- " + role_or_channel.name
                    )
            else:
                if role_or_channel == ctx.channel:
                    raise RequireCheckFailure(
                        blacklist["response"]
                        or "Blacklisted Channel\n- " + role_or_channel.name
                    )

    def role_or_channel_convert(self, ctx: CommandContext, argument: str):
        # try roles
        argument = argument.strip()
        if argument.startswith("<@&"):
            argument = argument[3:-1]

        if argument.isdigit():
            if role := ctx.guild.get_role(int(argument)):
                return role
            if channel := ctx.guild.get_channel(int(argument)):
                return channel

        result = utils.find(
            lambda x: x.name.lower() == argument.lower(),
            ctx.guild.roles + ctx.guild.text_channels,
        )
        if result is not None:
            return result
        try:
            name, ra = process.extractOne(
                argument,
                [x.name for x in ctx.guild.roles]
                + [x.name for x in ctx.guild.text_channels],
            )
        except TypeError:
            pass
        else:
            if ra >= 85:  # loop?
                return utils.get(ctx.guild.roles, name=name) or utils.get(
                    ctx.guild.channels, name=name
                )

        raise CheckFailure(
            "Role/Channel `{}` not found!".format(argument),
        )
