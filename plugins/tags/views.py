from squid.models.views import ButtonData, View
from squid.bot import ComponentContext
from discord.ui import Button


class TagView(View):
    KEY = "tag"

    def __init__(self, *a, key: str, **k):
        super().__init__()
        key = ButtonData(self.KEY, key=key)
        self.add_item(Button(*a, custom_id=key.store(), **k))

    @staticmethod
    def callback(self, ctx: ComponentContext, key: str):
        ...
