from .models import Interaction


class SquidContext(object):
    def __init__(self, bot, interaction: Interaction):
        self.interaction = interaction
        self.bot = bot

        self.interaction_id = interaction.id
        self.application_id = interaction.application_id
        self.interaction_type = interaction.type
        self.interaction_data = interaction.data
        self.guild_id = interaction.guild_id
        self.channel_id = interaction.channel_id

        self._user = {"user": interaction.user, "member": interaction.member}

        self._token = interaction.token
        self._message = interaction.message

    @property
    def token(self):
        return self._token

    def __repr__(self):
        return "<SquidContext: {}>".format(self.interaction)

    def invoke(self, command, *args, **kwargs):
        return command(self, *args, **kwargs)

    def send(self, *a, **k):
        with self.bot.webhook(self.application_id, self.token) as hook:
            return hook.send(*a, **k)
