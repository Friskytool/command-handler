from typing import TYPE_CHECKING, List, Optional

from discord import InteractionType
from .enums import ApplicationCommandOptionType


class Tag(object):
    if TYPE_CHECKING:
        name: str
        description: Optional[str]
        type: InteractionType
        author_id: int
        command_id: int
        guild_id: int

        # the actual tagscript to be processed
        tagscript: str
        uses: int
        options: List["TagArgument"]

    def __init__(self, *, state, data):
        self._state = state
        self._from_data(data)

    def _from_data(self, data: dict):
        self.name = data["name"]
        self.tagscript = data["tagscript"]
        self.description = data.get("description", "")
        self.author_id = data["author_id"]
        self.command_id = int(data["command_id"])
        self.uses = data.get("uses", 0)
        self.options = [TagArgument(state=self._state, data=d) for d in data["options"]]

    def run(self, interpreter, seed_variables: dict, **kw) -> Optional[str]:
        return interpreter.process(self.tagscript, seed_variables, **kw)


class TagArgument(object):
    if TYPE_CHECKING:
        name: str
        description: str
        type: ApplicationCommandOptionType
        required: bool

    def __init__(self, *, state, data):
        self._state = state
        self._from_data(data)

    def _from_data(self, data: dict):
        self.name = data["name"]
        self.description = data["description"]
        self.type = ApplicationCommandOptionType(data["type"])
        self.required = data.get("required", False)
