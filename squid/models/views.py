from typing import List, Dict, Any
from discord.ui import View as _View, Button
from discord.ui.view import _ViewWeights, Item
from itertools import groupby
import json
from typing import TYPE_CHECKING
from discord import Color, Embed
from squid.models.interaction import InteractionResponse


if TYPE_CHECKING:
    from squid.bot.context import ComponentContext


class ButtonData:
    def __init__(self, typ, **data: dict):
        self.typ = typ
        self.data = data

    def get_data(self):
        print(f"ButtonData.get_data: {self.typ} -> {self.data}")

    def store(self):
        return json.dumps(self.__dict__)

    def __repr__(self):
        return f"<ButtonData: {self.typ} {self.data}>"

    @classmethod
    def get(cls, data: str):
        obj = cls.__new__(cls)
        obj.__dict__ = json.loads(data)
        return obj


class View(_View):
    KEY: str

    def __init__(self):
        self.children = []
        self._View__weights = _ViewWeights([])

    def to_components(self) -> List[Dict[str, Any]]:
        def key(item: Item) -> int:
            return item._rendered_row or 0

        children = sorted(self.children, key=key)
        components: List[Dict[str, Any]] = []
        for _, group in groupby(children, key=key):
            children = [item.to_component_dict() for item in group]
            if not children:
                continue

            components.append(
                {
                    "type": 1,
                    "components": children,
                }
            )
        return components

    def callback(self, ctx: "ComponentContext"):
        raise NotImplementedError
