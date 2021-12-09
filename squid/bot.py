from command import SquidCommand
from discord import Embed, Color

class SquidBot(object):
    def __init__(self, public_key):
        self.public_key = public_key
    
        self._commands = {}
    
    def add_comand(self, command):
        if not isinstance(command, SquidCommand):
            raise ValueError("command must be of type SquidCommand")
        self._commands[command.name] = command
        
    def remove_command(self, command_name):
        return self._commands.pop(command_name, None)
    
    def unknown_command(self, interaction):
        return Embed(title="Unknown command", description="Unknown command: {}".format(interaction.data.name), color=Color.red())

    def handle_command(self, interaction):
        command = self._commands.get(interaction.data.name)
        if command is None:
            return self.unknown_command(interaction)
        
        return command.handle(interaction)