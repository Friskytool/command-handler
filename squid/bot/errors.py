class SquidError(Exception):
    """Base exception all other exceptions inherit from"""

    pass


class CommandFailed(SquidError):
    """
    Command processing failed through incorrect user input
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class BotInInput(CommandFailed):
    """
    A bot is in the input of the command
    """

    def __init__(self, message="I don't track bots"):
        super().__init__(message)


class CommandError(SquidError):
    """
    Command processing had an unexpected error
    """

    pass


class CheckFailure(CommandFailed):
    """
    A check failed
    """

    pass
