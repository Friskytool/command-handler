from functools import wraps
from typing import Callable, Optional

from expr.errors import Gibberish, NumberOverflow, UnknownPointer

from squid.bot.errors import CheckFailure, CommandFailed, SquidError
from squid.models.check import Check
from squid.models.interaction import Interaction
from .command import SquidCommand
from discord import Embed, Color
from .plugin import SquidPlugin
from discord import Webhook, RequestsWebhookAdapter
from squid.models.functions import Lazy
from .command import command
from .context import SquidContext
from squid.flask_support import flask_compat


class SquidBot(object):
    def __init__(
        self,
        *,
        public_key,
        # colors
        primary_color=Color.green(),
        secondary_color=Color.blurple(),
        error_color=Color.red(),
        # databases
        adapter=RequestsWebhookAdapter,
        **attrs,
    ):
        self.public_key = public_key

        self.colors = {
            "primary": primary_color,
            "secondary": secondary_color,
            "error": error_color,
        }

        self.__plugins = {}

        self._commands = {}
        self._checks = []

        self.adapter = Lazy(adapter)

        self.__dict__.update(
            {k[6:]: v for k, v in attrs.items() if k.startswith("squid_")}
        )

    @classmethod
    def from_lazy(cls, lazy_cls=Lazy):
        def wrapper(setup_fn: Callable):
            return wraps(setup_fn)(lazy_cls(setup_fn, cls))

        return wrapper

    def webhook(self, application_id, interaction_token):
        with self.adapter as adapter:
            return Lazy(
                Webhook.partial, application_id, interaction_token, adapter=adapter
            )

    @property
    def plugins(self):
        return self.__plugins.values()

    def add_plugin(self, plugin: SquidPlugin) -> SquidPlugin:
        if not isinstance(plugin, SquidPlugin):
            raise ValueError("plugin must be of type SquidPlugin")

        self.__plugins[plugin.qualified_name] = plugin
        plugin._inject(self)
        return plugin

    def remove_plugin(self, plugin_name: str) -> Optional[SquidPlugin]:
        plugin = self.__plugins.pop(plugin_name, None)
        if plugin is not None:
            plugin._eject(self)

        return plugin

    def get_command(self, command_name: str) -> Optional[SquidCommand]:
        return self._commands.get(command_name, None)

    def add_command(self, command: SquidCommand) -> SquidCommand:
        if not isinstance(command, SquidCommand):
            raise ValueError("command must be of type SquidCommand")
        self._commands[command.qualified_name] = command
        return command

    def remove_command(self, command_name: str) -> Optional[SquidCommand]:
        return self._commands.pop(command_name, None)

    def unknown_command(self, interaction: Interaction) -> Embed:
        return Embed(
            title="Unknown Interaction",
            description="Unknown interaction: {}".format(interaction.data.name),
            color=Color.red(),
        )

    def get_context(self, interaction, cls=SquidContext):
        return cls(self, interaction)

    def on_error(self, ctx: SquidContext, error: Exception):
        if isinstance(error, NumberOverflow):
            return Embed(
                title="Number Overflow",
                description="The number you entered is too large.",
                color=ctx.bot.colors["error"],
            )
        if isinstance(error, (UnknownPointer, Gibberish)):
            return Embed(
                title="Gibberish",
                description=f"```cs\n{error.friendly}\n```",
                color=ctx.bot.colors["error"],
            )
        return Embed(
            title="".join(
                [(" " if i.isupper() else "") + i for i in error.__class__.__name__]
            ),
            description=f"```cs\n[ERROR] {str(error)}\n```".replace("'", "′"),
            color=self.colors["error"],
        )

    def invoke(self, ctx: SquidContext) -> Optional[Embed]:
        try:
            if ctx.command is not None:
                if self.can_run(ctx):
                    return ctx.invoke(ctx.command)
                raise CheckFailure("The global check failed")
            else:
                return self.unknown_command(ctx.interaction)
        except SquidError as e:
            return self.on_error(ctx, e)
        else:
            pass  # command completion code

    def can_run(self, ctx: SquidContext) -> bool:
        return all(check(ctx) for check in self._checks) if self._checks else True

    def check(self, func):
        self.add_check(func)
        return func

    def add_check(self, func: Check) -> None:
        self._checks.append(func)

    def remove_check(self, func: Check) -> None:
        try:
            self._checks.remove(func)
        except ValueError:
            pass

    @flask_compat
    def process(self, interaction):
        command = self._commands.get(interaction.data.name)
        if command is None:
            return self.unknown_command(interaction)

        ctx = self.get_context(interaction)

        return self.invoke(ctx)
