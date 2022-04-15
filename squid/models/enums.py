from enum import Enum

__all__ = (
    "ApplicationCommandType",
    "ApplicationCommandOptionType",
)


class ApplicationCommandType(Enum):
    chat_input = (
        1  # Slash commands; a text-based command that shows up when a user types /
    )
    user = 2  # A UI-based command that shows up when you right click or tap on a user
    message = (
        3  # A UI-based command that shows up when you right click or tap on a message
    )


class ApplicationCommandOptionType(Enum):
    sub_command = 1
    sub_command_group = 2
    string = 3
    integer = 4
    boolean = 5
    user = 6
    channel = 7
    role = 8
    mentionable = 9
    number = 10
