from __future__ import annotations

from typing import List, Any, Type
from squid import utils
from .command import SquidCommand, _BaseCommand
import inspect


class PluginMeta(type):

    __cog_name__: str
    __cog_commands__: List[SquidCommand]

    def __new__(cls: Type[PluginMeta], *args: Any, **kwargs: Any) -> PluginMeta:
        name, bases, attrs = args
        attrs["__cog_name__"] = utils.camel_to_snake(kwargs.pop("name", name))
        attrs["__cog_settings__"] = kwargs.pop("command_attrs", {})

        description = kwargs.pop("description", None)
        if description is None:
            description = inspect.cleandoc(attrs.get("__doc__", ""))
        attrs["__cog_description__"] = description

        commands = {}
        no_bot_cog = "Commands or listeners must not start with cog_ or bot_ (in method {0.__name__}.{1})"

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in commands:
                    del commands[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, _BaseCommand):
                    if is_static_method:
                        raise TypeError(
                            f"Command in method {base}.{elem!r} must not be staticmethod."
                        )
                    if elem.startswith(("cog_", "bot_")):
                        raise TypeError(no_bot_cog.format(base, elem))
                    commands[elem] = value

        new_cls.__cog_commands__ = list(
            commands.values()
        )  # this will be copied in Cog.__new__

        return new_cls


class SquidPlugin(metaclass=PluginMeta):
    def __new__(cls, *args: Any, **kwargs: Any):
        # For issue 426, we need to store a copy of the command objects
        # since we modify them to inject `self` to them.
        # To do this, we need to interfere with the Cog creation process.
        self = super().__new__(cls)
        cmd_attrs = cls.__cog_settings__
        # Either update the command with the cog provided defaults or copy it.
        # r.e type ignore, type-checker complains about overriding a ClassVar
        self.__cog_commands__ = tuple(c._update_copy(cmd_attrs) for c in cls.__cog_commands__)  # type: ignore

        lookup = {cmd.qualified_name: cmd for cmd in self.__cog_commands__}

        # Update the Command instances dynamically as well
        for command in self.__cog_commands__:
            setattr(self, command.callback.__name__, command)
            parent = command.parent
            if parent is not None:
                # Get the latest parent reference
                parent = lookup[parent.qualified_name]  # type: ignore

                # Update our parent's reference to our self
                parent.remove_command(command.name)  # type: ignore
                parent.add_command(command)  # type: ignore

        return self

    def get_commands(self):
        r"""
        Returns
        --------
        List[:class:`.Command`]
            A :class:`list` of :class:`.Command`\s that are
            defined inside this cog.
            .. note::
                This does not include subcommands.
        """
        return [c for c in self.__cog_commands__ if c.parent is None]

    @property
    def qualified_name(self) -> str:
        """:class:`str`: Returns the cog's specified name, not the class name."""
        return self.__cog_name__

    @property
    def db_name(self) -> str:
        return self.qualified_name.lower()

    @property
    def description(self) -> str:
        """:class:`str`: Returns the cog's description, typically the cleaned docstring."""
        return self.__cog_description__

    @description.setter
    def description(self, description: str) -> None:
        self.__cog_description__ = description

    def _inject(self, bot):
        for index, command in enumerate(self.__cog_commands__):
            command.cog = self
            if command.parent is None:
                try:
                    bot.add_command(command)
                except Exception as e:
                    # undo our additions
                    for to_undo in self.__cog_commands__[:index]:
                        if to_undo.parent is None:
                            bot.remove_command(to_undo.name)
                    raise e

        return self

    def _eject(self, bot):

        try:
            for command in self.__cog_commands__:
                if command.parent is None:
                    bot.remove_command(command.name)
        finally:
            try:
                self.cog_unload()
            except Exception:
                pass
