from ast import arg
from ctypes import Union
import inspect
from tokenize import Double
from typing import TYPE_CHECKING, List, Optional
from squid.models.enums import ApplicationCommandType
from squid.models.enums import ApplicationCommandOptionType
from squid.models.interaction import ApplicationCommandOption

if TYPE_CHECKING:
    from squid.bot.command import SquidCommand


class CreateApplicationCommand(object):
    def __init__(
        self,
        name: str,
        description: str,
        options: List["ApplicationCommandOption"],
        default_permissions: Optional[bool] = None,
        type: Optional[ApplicationCommandType] = ApplicationCommandType.chat_input,
    ):
        self.name = name
        self.description = description
        self.options = options
        self.default_permissions = default_permissions
        self.type = type

    def __repr__(self):
        return f"<CreateApplicationCommand name={self.name!r} description={self.description!r} options={self.options!r} default_permissions={self.default_permissions!r} type={self.type!r}>"

    def get_annotated_type(
        typ: object = str, name: str = None
    ) -> ApplicationCommandOptionType:
        if typ == int:
            return ApplicationCommandOptionType.number
        elif typ == bool:
            return ApplicationCommandOptionType.boolean
        elif typ == str:
            return ApplicationCommandOptionType.string

        if name:
            try:
                return getattr(ApplicationCommandOptionType, name.lower())
            except AttributeError:
                pass

        raise ValueError(f"Unknown type ({typ}): {name}")

    @classmethod
    def from_command(cls, cmd: "SquidCommand", type=ApplicationCommandType.chat_input):
        options = []

        for c in cmd.commands:
            if c.commands:  # is a sub command group
                ty = ApplicationCommandOptionType.sub_command_group
            else:
                ty = ApplicationCommandOptionType.sub_command

            options.append(cls.from_command(c, type=ty))

        # adding arguments for base command
        argspec = inspect.getfullargspec(cmd.callback)
        if cmd.cog:
            argspec.args.remove("self")
        if "ctx" not in argspec.args:
            raise ValueError("Callback must have a ctx argument")
        else:
            argspec.args.remove("ctx")

        for arg in argspec.args:
            options.append(
                ApplicationCommandOption(
                    state=None,
                    data=dict(
                        name=arg,
                        description="Enter the value for the argument",
                        type=cls.get_annotated_type(
                            argspec.annotations.get(arg, str), arg
                        ),
                        required=arg in argspec.args[: -len(argspec.defaults or [])],
                        options=[],
                    ),
                )
            )
        return cls(
            name=cmd.name,
            description=cmd.help,
            options=options,
            default_permissions=cmd.enabled,
            type=type,
        )

    def serialize(self):
        return {
            "name": self.name,
            "description": self.description,
            "options": [option.serialize() for option in self.options],
            "default_permissions": self.default_permissions,
            "type": self.type.value,
        }
