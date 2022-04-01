from functools import wraps
import traceback
from typing import TYPE_CHECKING, Callable, Optional
import sentry_sdk
from expr.errors import Gibberish, NumberOverflow, UnknownPointer
import requests
from pprint import pprint
from squid.bot.errors import CheckFailure, SquidError
from squid.models.enums import InteractionType
from squid.models.interaction import Interaction, InteractionResponse
from squid.http import HttpClient
from squid.models.views import View
from .command import SquidCommand
from discord import Embed, Color
from .plugin import SquidPlugin
from discord import SyncWebhook as Webhook
from squid.models.functions import Lazy
from .context import CommandContext, ComponentContext, SquidContext
from squid.flask_support import flask_compat


class SquidBot(object):
    def __init__(
        self,
        *,
        public_key: str,
        token: str,
        # colors
        primary_color=Color.green(),
        secondary_color=Color.blurple(),
        error_color=Color.red(),
        # databases
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
        self._handlers = {}
        self._checks = []
        self.session = requests.Session()

        self.http = HttpClient(token, session=self.session)

        self.__dict__.update(
            {k[6:]: v for k, v in attrs.items() if k.startswith("squid_")}
        )

    @classmethod
    def from_lazy(cls, lazy_cls=Lazy):
        def wrapper(setup_fn: Callable):
            return wraps(setup_fn)(lazy_cls(setup_fn, cls))

        return wrapper

    def webhook(self, application_id, interaction_token):
        return Lazy(Webhook.partial, application_id, interaction_token)

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

    def get_handler(self, handler_name: str) -> Optional[Callable]:
        return self._handlers.get(handler_name, None)

    def add_handler(self, handler: View) -> None:
        self._handlers[handler.KEY] = handler

    def remove_handler(self, handler_name: str) -> Optional[Callable]:
        return self._handlers.pop(handler_name, None)

    def unknown_command(self, ctx: CommandContext) -> InteractionResponse:
        return InteractionResponse.channel_message(
            embed=Embed(
                title="Unknown Interaction",
                description=f"Unknown interaction: {ctx.interaction.data.name}",
                color=self.colors["error"],
            ),
            ephemeral=True,
        )

    def unknown_component(self, interaction: Interaction) -> InteractionResponse:
        return InteractionResponse.channel_message(
            embed=Embed(
                title="Unknown Component",
                description="This issue will be fixed soon ;(",
                color=Color.red(),
            ),
            ephemeral=True,
        )

    def get_context(self, interaction, cls=CommandContext):
        return cls(self, interaction)

    def on_error(self, ctx: CommandContext, error: Exception) -> InteractionResponse:
        print(repr(error))
        if isinstance(error, NumberOverflow):
            embed = Embed(
                title="Number Overflow",
                description="The number you entered is too large.",
                color=ctx.bot.colors["error"],
            )
        elif isinstance(error, (UnknownPointer, Gibberish)):
            embed = Embed(
                title="Gibberish",
                description=f"```cs\n{error.friendly}\n```",
                color=ctx.bot.colors["error"],
            )
        elif isinstance(error, CheckFailure):
            embed = Embed(
                title="Check Failure",
                description=error.message,
                color=ctx.bot.colors["error"],
            )
        else:
            embed = Embed(
                title="".join(
                    [(" " if i.isupper() else "") + i for i in error.__class__.__name__]
                ),
                description=f"```cs\n[ERROR] {str(error)}\n```".replace("'", "′"),
                color=self.colors["error"],
            )
            traceback.print_exc()
        return InteractionResponse.channel_message(embed=embed, ephemeral=True)

    def invoke(self, ctx: SquidContext) -> Optional[InteractionResponse]:
        if ctx.interaction.type == InteractionType.APPLICATION_COMMAND:
            pprint(ctx)
            try:
                if ctx.command is None:
                    return self.unknown_command(ctx)
                if self.can_run(ctx):
                    sentry_sdk.set_context(
                        "command",
                        {"name": ctx.command.qualified_name, "ctx": ctx},
                    )
                    return ctx.command.invoke(ctx)
                raise CheckFailure("This command is disabled")
            except Exception as e:
                return self.on_error(ctx, e)
        elif ctx.interaction.type == InteractionType.MESSAGE_COMPONENT:
            try:
                if ctx.handler is None:
                    return self.unknown_component(ctx.interaction)
                if self.can_run(ctx):
                    sentry_sdk.set_context(
                        "message-component",
                        {"name": ctx.data.typ, "ctx": ctx},
                    )
                    return ctx.invoke(ctx.handler)
                raise CheckFailure("This component is disabled")
            except SquidError as e:
                return self.on_error(ctx, e)
        else:
            return None

    def can_run(self, ctx: CommandContext) -> bool:
        if len(self._checks) > 0:
            return all(check(ctx) for check in self._checks)
        else:
            return True

    def check(self, func):
        self.add_check(func)
        return func

    def add_check(self, func: Callable) -> None:
        self._checks.append(func)

    def remove_check(self, func: Callable) -> None:
        try:
            self._checks.remove(func)
        except ValueError:
            pass

    @flask_compat
    def process(self, interaction: Interaction):
        if interaction.type == InteractionType.APPLICATION_COMMAND:
            ctx = self.get_context(interaction)
            if ctx.command is None:
                return self.unknown_command(ctx)

        elif interaction.type == InteractionType.MESSAGE_COMPONENT:

            ctx = self.get_context(interaction, cls=ComponentContext)

            if ctx.handler is None:
                return self.unknown_component(interaction)
        return self.invoke(ctx)
