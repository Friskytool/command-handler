from typing import TYPE_CHECKING, Any, Dict
from squid.models.settings import Setting
import TagScriptEngine as tse
from inspect import isfunction
import json

from collections import OrderedDict

if TYPE_CHECKING:
    from squid.bot.context import CommandContext, SquidContext


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class Settings(object):
    def __init__(self, settings: Dict[str, Setting]):
        self.settings = settings
        self.cache = LimitedSizeDict(
            size_limit=5
        )  # just for multiple concurrent data accesses

    @classmethod
    def from_data(cls, data: Dict[str, Dict[str, Any]]):
        for plugin, settings in data.items():
            for name, value in settings.items():
                data.setdefault(plugin, {})[name] = Setting.from_data(value)

        return cls(data)

    def _transform_seed_variables(self, seed_variables: dict) -> Dict[str, tse.Adapter]:
        data = {}
        for k, v in seed_variables.items():
            if isinstance(v, str):
                data[k] = tse.StringAdapter(v)
            elif isinstance(v, int):
                data[k] = tse.IntAdapter(v)
            elif isfunction(v):
                data[k] = tse.FunctionAdapter(v)
            elif isinstance(v, object):
                data[k] = tse.SafeObjectAdapter(v)
            else:
                raise TypeError(f"Unsupported type {type(v)}")
        return data

    def guild_settings(self, ctx: "CommandContext") -> dict:
        # if not (data := self.cache.get(ctx.guild_id)):
        with ctx.bot.db as db:
            data = db.settings.find_one({"guild_id": str(ctx.guild_id)}) or {}
        self.cache[ctx.guild_id] = data
        r = {}

        for v, k in self.settings.get(ctx.plugin.db_name, {}).items():

            r[v] = data.get(ctx.plugin.db_name, {}).get(v, k.default)
        return r

    def get(self, ctx: "CommandContext", name: str, **kw) -> str:
        settings_data = self.guild_settings(ctx)
        if name in settings_data:
            setting = settings_data.get(name)
            if len(kw.keys()) == 0:
                return setting

            # processing tagscript
            seed_variables = self._transform_seed_variables(kw)
            with ctx.bot.engine as engine:
                return engine.process(setting, seed_variables=seed_variables).body

        raise KeyError(name)
