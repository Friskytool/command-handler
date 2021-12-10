from typing import Optional
from .command import SquidCommand
from discord import Embed, Color
from .plugin import SquidPlugin
import requests
from discord import Webhook, RequestsWebhookAdapter
from .models.functions import Lazy
from .command import command
from .context import SquidContext
from .flask_support import flask_compat


def setup_bot(config_fn):
    """Helper function to delay bot initializiation until it's needed

    Returns:
        SquidBot: The created and setup bot
    """

    bot = SquidBot(config_fn("PUBLIC_KEY"))

    from plugins.utility import Utility

    bot.add_plugin(Utility(bot))

    return bot


class SquidBot(object):
    def __init__(self, public_key):
        self.public_key = public_key

        self.__plugins = {}

        self._commands = {}

        self.adapter = Lazy(RequestsWebhookAdapter)

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

    def add_command(self, command: SquidCommand) -> SquidCommand:
        if not isinstance(command, SquidCommand):
            raise ValueError("command must be of type SquidCommand")
        self._commands[command.qualified_name] = command
        return command

    def remove_command(self, command_name: str) -> Optional[SquidCommand]:
        return self._commands.pop(command_name, None)

    def unknown_command(self, interaction) -> Embed:
        return Embed(
            title="Unknown command",
            description="Unknown command: {}".format(interaction.data.name),
            color=Color.red(),
        )

    def get_context(self, interaction, cls=SquidContext):
        return cls(self, interaction)

    @flask_compat
    def process(self, interaction):
        command = self._commands.get(interaction.data.name)
        if command is None:
            return self.unknown_command(interaction)

        ctx = self.get_context(interaction)

        return ctx.invoke(command)
