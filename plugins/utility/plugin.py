from contextlib import redirect_stdout
import io
import shlex
import traceback
from discord import Color, Embed
import json
from plugins.giveaways.views import C
from squid.bot import command, SquidPlugin, CommandContext
import inspect
from discord.http import Route
from discord.ext import commands
from squid.bot.checks import has_role_named
from squid.bot.errors import CommandFailed
from squid.models.commands import CreateApplicationCommand
from squid.models.member import Member


class Utility(SquidPlugin):  # todo fill in cog
    def __init__(self, bot):
        self.bot = bot

    @command()
    def ping(self, ctx: CommandContext):
        """Pings the bot"""
        return ctx.respond(
            embed=Embed(
                description=f"Pong!\n",
                color=self.bot.colors["primary"],
            ),
            ephemeral=False,
        )

    @command(ignore_register=True)
    def register(self, ctx: CommandContext, command: str = None):
        """Registers commands"""
        if ctx.author.id != ctx.bot.owner_id:
            raise CommandFailed("You are not the owner of this bot.")

        if command == "all":
            command = None
        commands = ctx.http.get_guild_commands(ctx.bot.application_id, ctx.guild_id)
        commands = {c["id"]: c["name"] for c in commands}

        if not command:
            bot_commands = []
            for plugin in ctx.bot.plugins:
                for cmd in plugin.get_commands():
                    if cmd.name not in commands.values():
                        if cmd.ignore_register:
                            continue
                        bot_commands.append(
                            CreateApplicationCommand.from_command(cmd).serialize()
                        )
            c = 0
            for cmd in bot_commands:
                if cmd["name"] == "register":
                    continue
                ctx.http.upsert_guild_command(ctx.bot.application_id, ctx.guild_id, cmd)
                c += 1

            return ctx.respond(embed=Embed(description=f"Added {c:,} Commands..."))
        else:
            if c := ctx.bot.get_command(command):
                ctx.http.upsert_guild_command(
                    ctx.bot.application_id,
                    ctx.guild_id,
                    CreateApplicationCommand.from_command(c).serialize(),
                )
                return ctx.respond(content=f"{c.name} upserted.")
            else:

                try:
                    if ";" in command:
                        route, method, command = command.split(";")
                    data = json.loads(command)
                except json.JSONDecodeError:
                    if command.startswith("py:"):
                        env = {
                            "bot": self.bot,
                            "ctx": ctx,
                            "channel": ctx.channel,
                            "author": ctx.author,
                            "guild": ctx.guild,
                            "_": self.bot._last_result,
                        }
                        env.update(globals())
                        env.update(locals())

                        to_compile = f"def func():\n return {command[3:]}"

                        try:
                            exec(to_compile, env)
                        except Exception as e:
                            return ctx.respond(
                                content=f"```py\n{e.__class__.__name__}: {e}\n```"
                            )
                        else:
                            func = env["func"]
                            stdout = io.StringIO()
                            try:
                                with redirect_stdout(stdout):
                                    ret = func()
                            except Exception as e:
                                value = stdout.getvalue()
                                return ctx.respond(
                                    content=f"```py\n{value}{traceback.format_exc()}\n```"
                                )
                            else:
                                value = stdout.getvalue()

                                if ret is None and value:
                                    return ctx.respond(content=f"```py\n{value}\n```")
                                else:
                                    self.bot._last_result = ret
                                    return ctx.respond(
                                        content=f"```py\n{value}{ret}\n```"
                                    )

                    return ctx.respond(content=f"{command} is not a valid command.")
                else:
                    return ctx.respond(
                        content=str(
                            ctx.http.request(
                                Route(path=route, method=method), json=data
                            )
                        )
                    )

    @command()
    def links(self, ctx: CommandContext):
        """Get's the bot's invite links"""

        embed = Embed(
            color=ctx.bot.colors["primary"],
            title="Invite Links",
            description=f"> [Invite link](Bot Invite)](https://discord.com/oauth2/authorize?client_id={0}&scope=bot%20applications.commands&permissions=1611000937)\n\n> [Invite Link (Support server)](https://discord.gg/TMu242J)\n\n> [Click this link to vote!](https://top.gg/bot/700743797977514004/vote)",
        )

        return ctx.respond(embed=embed)

    @command()
    def about(self, ctx: CommandContext):
        """
        Information about the bot
        """

        data = """
        Created By:\u200b \u200b[`Squidtoon99`](https://squid.pink) & Frisky\n\u200b
        Premium:\u200b    \u200bhttps://patreon.com/friskytool\n\u200b
        Website:\u200b    \u200bhttps://frisky.dev\n\u200b
        Support Server:\u200b \u200b[discord.gg/TMu242J](https://discord.com/invite/TMu242J)\n\u200b
        """
        return ctx.respond(
            embed=Embed(
                description=inspect.cleandoc(data).strip(),
                color=self.bot.colors["primary"],
            )
        )

    @command()
    @commands.check(has_role_named("afk_roles"))
    def afk(self, ctx: CommandContext, message: str = None):
        """Set an afk message that will be sent when you are pinged"""
        with ctx.bot.redis as redis:
            data = redis.get(f"afk.{ctx.guild_id}.{ctx.author.id}")
            if not data or message:
                message = message or "I'm AFK"
                redis.set(
                    f"afk.{ctx.guild_id}.{ctx.author.id}", message[:500], ex=4838400
                )

                return ctx.respond(
                    embed=Embed(
                        color=ctx.bot.colors["primary"],
                        title="Set AFK",
                        description=f"I set your afk to `{message[:500]}`",
                    )
                )

            redis.delete(f"afk.{ctx.guild_id}.{ctx.author.id}")

            return ctx.respond(
                embed=Embed(
                    color=ctx.bot.colors["secondary"],
                    title="Removed AFK",
                    description="I removed your afk",
                )
            )

    @command()
    @commands.has_guild_permissions(administrator=True)
    def afkadmin(self, ctx: CommandContext):
        """Admin commands for managing afk users"""
        ...

    @afkadmin.subcommand(name="clear")
    @commands.has_guild_permissions(administrator=True)
    def clear(self, ctx: CommandContext, user: Member):
        """Clear the afk message of a given user"""
        with ctx.bot.redis as redis:
            redis.delete(f"afk.{ctx.guild_id}.{user.id}")
        return ctx.respond(
            embed=Embed(
                color=ctx.bot.colors["primary"],
                description=f"Removed AFK message from {user.mention}",
                title="Removed AFK",
            )
        )

    @afkadmin.subcommand(name="set")
    @commands.has_guild_permissions(administrator=True)
    def set(self, ctx: CommandContext, user: Member, message: str):
        """set the afk message of a given user"""
        with ctx.bot.redis as redis:
            redis.set(f"afk.{ctx.guild_id}.{user.id}", message[:500], ex=4838400)
        return ctx.respond(
            embed=Embed(
                color=ctx.bot.colors["primary"],
                description=f"Set the AFK message of {user.mention}",
                title="Set AFK",
            )
        )

    @command(name="poll")
    def poll(self, ctx: CommandContext, question: str):
        """
        Create a poll
        """

        return ctx.respond(
            embed=Embed(
                title=question.replace("`", "\\`"),
                color=Color.purple(),
            ).set_author(icon_url=ctx.author.avatar.url, name=ctx.author.name)
        )

    @command(name="quickpoll")
    def quickpoll(self, ctx: CommandContext, questions_and_choices: str):
        """Quickly setup a poll for the bot to run"""
        for i in ["|", ","]:
            if i in questions_and_choices:
                questions_and_choices = questions_and_choices.split(i)
                break
        else:
            questions_and_choices = shlex.split(questions_and_choices)

        if len(questions_and_choices) < 3:
            raise CommandFailed(
                "Need at least 1 question with 2 choices. Use poll for just a yes/no question",
                hint="You can seperate questions and choices with `,`",
            )
        elif len(questions_and_choices) > 11:
            raise CommandFailed("You can only have up to 10 choices.")

        question = questions_and_choices.pop(0)  # easier for enumerate
        choices = [
            (self.to_keycap(pos), item.replace("`", "\\`"))
            for pos, item in enumerate(questions_and_choices, 1)
        ]
        question.replace("`", "\\`")

        return ctx.respond(
            embed=Embed(
                description="\n".join(
                    [f"`{pos+1}.` **{query[1]}**" for pos, query in enumerate(choices)]
                ),
                color=Color.purple(),
            ).set_author(name=f"{ctx.author.display_name} asks {question}")
        )

    @command()
    def vote(self, ctx: CommandContext):
        """Vote for the bot on voting platforms"""
        return ctx.respond(
            embed=Embed(
                title="Support the Bot!",
                description=f"Voting helps us reach new users and is a great way to support the bot without paying\n\n[Top.gg](https://top.gg/bot/{self.bot.application_id})",
                color=self.bot.colors["primary"],
            )
        )


def setup(bot):
    bot.add_plugin(Utility(bot))
