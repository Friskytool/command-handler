from typing import List


class SquidError(Exception):
    """Base exception all other exceptions inherit from"""

    pass


class CommandFailed(SquidError):
    """
    Command processing failed through incorrect user input
    """

    def __init__(self, *args: List[str], fmt="cs", **opts):
        super().__init__(*args)

        if opts.get("raw", False):
            self.message = "\n".join(args)
        else:
            self.fmt = fmt
            self.message = (
                (f"```{fmt}\n" if fmt else "```\n")
                + ("[ERROR] " if fmt == "cs" else "")
                + "\n".join(args).replace("'", "′").replace("`", "′")
                + "\n```"
            )
        self.title = opts.get("title", "Command Error")
        print(self.message)

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

    def __init__(self, *a, **kw):
        kw.setdefault("fmt", "diff")
        super().__init__(*a, **kw)


class RequireCheckFailure(CheckFailure):
    ...
