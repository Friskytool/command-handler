from typing_extensions import Self
from squid._types import _BaseCommand
from typing import Callable, Any, Optional, List, Union, Dict, Tuple, Type, TypeVar
import inspect
from squid.bot.errors import CheckFailure, CommandError
from squid.utils import evaluate_annotation
from .context import CommandContext
from squid.errors import ArgumentParsingError
from .converter import get_converter
import functools

CommandT = TypeVar("CommandT", bound="SquidCommand")
T = TypeVar("T")


def get_signature_parameters(
    function: Callable[..., Any], globalns: Dict[str, Any]
) -> Dict[str, inspect.Parameter]:
    signature = inspect.signature(function)
    params = {}
    cache: Dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        annotation = parameter.annotation
        if annotation is parameter.empty:
            params[name] = parameter
            continue
        if annotation is None:
            params[name] = parameter.replace(annotation=type(None))
            continue

        annotation = evaluate_annotation(annotation, globalns, globalns, cache)
        params[name] = parameter.replace(annotation=annotation)

    return params


def unwrap_function(function: Callable[..., Any]) -> Callable[..., Any]:
    partial = functools.partial
    while True:
        if hasattr(function, "__wrapped__"):
            function = function.__wrapped__
        elif isinstance(function, partial):
            function = function.func
        else:
            return function


class _CaseInsensitiveDict(dict):
    def __contains__(self, k):
        return super().__contains__(k.casefold())

    def __delitem__(self, k):
        return super().__delitem__(k.casefold())

    def __getitem__(self, k):
        return super().__getitem__(k.casefold())

    def get(self, k, default=None):
        return super().get(k.casefold(), default)

    def pop(self, k, default=None):
        return super().pop(k.casefold(), default)

    def __setitem__(self, k, v):
        super().__setitem__(k.casefold(), v)


class SquidCommand(_BaseCommand):
    """
    Mostly copies from discord.py but modified for our purposes.
    """

    __original_kwargs__: Dict[str, Any]

    def __new__(cls: Type[CommandT], *args: Any, **kwargs: Any) -> CommandT:
        # if you're wondering why this is done, it's because we need to ensure
        # we have a complete original copy of **kwargs even for classes that
        # mess with it by popping before delegating to the subclass __init__.
        # In order to do this, we need to control the instance creation and
        # inject the original kwargs through __new__ rather than doing it
        # inside __init__.
        self = super().__new__(cls)

        # we do a shallow copy because it's probably the most common use case.
        # this could potentially break if someone modifies a list or something
        # while it's in movement, but for now this is the cheapest and
        # fastest way to do what we want.
        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self, func, **kwargs):
        name = kwargs.get("name") or func.__name__
        if not isinstance(name, str):
            raise TypeError("Name of a command must be a string.")
        self.name: str = name

        self.callback = func
        self.enabled: bool = kwargs.get("enabled", True)

        help_doc = kwargs.get("help")
        if help_doc is not None:
            help_doc = inspect.cleandoc(help_doc)
        else:
            help_doc = inspect.getdoc(func)
            if isinstance(help_doc, bytes):
                help_doc = help_doc.decode("utf-8")

        self.help: Optional[str] = help_doc

        self.brief: Optional[str] = kwargs.get("brief")
        self.usage: Optional[str] = kwargs.get("usage")

        # for a future register command to associate commands with groups
        self.group: Optional[str] = kwargs.get("group")

        self.aliases: Union[List[str], Tuple[str]] = kwargs.get("aliases", [])
        self.extras: Dict[str, Any] = kwargs.get("extras", {})

        if not isinstance(self.aliases, (list, tuple)):
            raise TypeError(
                "Aliases of a command must be a list or a tuple of strings."
            )

        self.description: str = inspect.cleandoc(kwargs.get("description", ""))
        self.hidden: bool = kwargs.get("hidden", False)

        parent = kwargs.get("parent")
        self.parent = parent if isinstance(parent, _BaseCommand) else None  # type: ignore

        try:
            checks = func.__commands_checks__
            checks.reverse()
        except AttributeError:
            checks = kwargs.get("checks", [])

        self.cog = kwargs.get("cog")

        self.checks: List[Callable] = checks
        self._commands: Dict[str, Type[Self]] = {}

    def __repr__(self):
        return f"<SquidCommand name={self.name!r} qualified_name={self.qualified_name!r} commands={self._commands!r}>"

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, value):
        if not callable(value):
            raise TypeError("Callback of a command must be a callable.")
        self._callback = value

        unwrap = unwrap_function(value)
        try:
            globalns = unwrap.__globals__
        except AttributeError:
            globalns = {}

        self.params = get_signature_parameters(value, globalns)

    def add_check(self, func: Callable, /) -> None:
        """Adds a check to the command.
        This is the non-decorator interface to :func:`.check`.
        Parameters
        -----------
        func
            The function that will be used as a check.
        """

        self.checks.append(func)

    def remove_check(self, func: Callable, /) -> None:
        """Removes a check from the command.
        This is the non-decorator interface to :func:`.check`.
        Parameters
        -----------
        func
            The function to remove from the checks.
        """
        try:
            self.checks.remove(func)
        except ValueError:
            pass

    def update(self, **kwargs: Any) -> None:
        """Updates :class:`Command` instance with updated attribute.
        This works similarly to the :func:`.command` decorator in terms
        of parameters in that they are passed to the :class:`Command` or
        subclass constructors, sans the name and callback.
        """
        self.__init__(self.callback, **dict(self.__original_kwargs__, **kwargs))

    def can_run(self, ctx: CommandContext):
        original = ctx.command
        ctx.command = self
        try:
            if not ctx.bot.can_run(ctx):
                raise CheckFailure(
                    f"The global check functions for command {self.name} failed."
                )

            cog = self.cog

            if cog is not None:
                try:
                    local_check = cog.cog_check

                except AttributeError:
                    local_check = None
                if local_check is not None:
                    if not cog.cog_check(ctx):
                        return False

            if not self.checks:
                return True

            return all(map(lambda check: check(ctx), self.checks))
        finally:
            ctx.command = original

    def prepare(self, ctx: CommandContext):
        try:
            if not self.can_run(ctx):
                raise CheckFailure(
                    "The check functions for command {0.name} failed.".format(self)
                )
        except CheckFailure as exc:
            raise exc
        except Exception as e:
            raise CommandError(str(e)) from e

    def invoke(self, ctx: CommandContext):
        """Invokes the command given the ctx."""
        self.prepare(ctx)

        return self(ctx, **ctx.kwargs)

    def __call__(self, context: CommandContext, *args, **kwargs):
        """|coro|
        Calls the internal callback that the command holds.
        .. note::
            This bypasses all mechanisms -- including checks, converters,
            invoke hooks, cooldowns, etc. You must take care to pass
            the proper arguments and types to this function.
        .. versionadded:: 1.3
        """
        if self.cog is not None:
            return self.callback(self.cog, context, *args, **kwargs)  # type: ignore
        return self.callback(context, *args, **kwargs)  # type: ignore

    def transform(self, ctx: CommandContext, param: inspect.Parameter) -> Any:
        required = param.default is param.empty
        converter = get_converter(param)
        consume_rest_is_special = (
            param.kind == param.KEYWORD_ONLY and not self.rest_is_raw
        )
        view = ctx.view
        view.skip_ws()

        # The greedy converter is simple -- it keeps going until it fails in which case,
        # it undos the view ready for the next parameter to use instead

        if view.eof:
            if param.kind == param.VAR_POSITIONAL:
                raise RuntimeError()  # break the loop
            if required:
                if self._is_typing_optional(param.annotation):
                    return None
                if (
                    hasattr(converter, "__commands_is_flag__")
                    and converter._can_be_constructible()
                ):
                    return converter._construct_default(ctx)
                raise ArgumentParsingError(param)
            return param.default

        previous = view.index
        if consume_rest_is_special:
            argument = view.read_rest().strip()
        else:
            try:
                argument = view.get_quoted_word()
            except ArgumentParsingError as exc:
                if self._is_typing_optional(param.annotation):
                    view.index = previous
                    return None
                raise exc
        view.previous = previous

        # type-checker fails to narrow argument
        return run_converters(ctx, converter, argument, param)  # type: ignore

    def _ensure_assignment_on_copy(self, other):

        # if I start adding checks they should be added here

        if self.checks != other.checks:
            other.checks = self.checks.copy()
        try:
            other.on_error = self.on_error
        except AttributeError:
            pass
        return other

    def _update_copy(self, kwargs: Dict[str, Any]):
        if kwargs:
            kw = kwargs.copy()
            kw.update(self.__original_kwargs__)
            copy = self.__class__(self.callback, **kw)
            return self._ensure_assignment_on_copy(copy)
        return self.copy()

    def copy(self: CommandT) -> CommandT:
        """Creates a copy of this command.
        Returns
        --------
        :class:`Command`
            A new instance of this command.
        """
        ret = self.__class__(self.callback, **self.__original_kwargs__)
        return self._ensure_assignment_on_copy(ret)

    @property
    def clean_params(self) -> Dict[str, inspect.Parameter]:
        """Dict[:class:`str`, :class:`inspect.Parameter`]:
        Retrieves the parameter dictionary without the context or self parameters.
        Useful for inspecting signature.
        """
        result = self.params.copy()
        if self.cog is not None:
            # first parameter is self
            try:
                del result[next(iter(result))]
            except StopIteration:
                raise ValueError("missing 'self' parameter") from None

        try:
            # first/second parameter is context
            del result[next(iter(result))]
        except StopIteration:
            raise ValueError("missing 'context' parameter") from None

        return result

    @property
    def full_parent_name(self) -> str:
        """:class:`str`: Retrieves the fully qualified parent command name.
        This the base command name required to execute it. For example,
        in ``?one two three`` the parent name would be ``one two``.
        """
        entries = []
        command = self
        # command.parent is type-hinted as GroupMixin some attributes are resolved via MRO
        while command.parent is not None:  # type: ignore
            command = command.parent  # type: ignore
            entries.append(command.name)  # type: ignore

        return " ".join(reversed(entries))

    @property
    def qualified_name(self) -> str:
        """:class:`str`: Retrieves the fully qualified command name.
        This is the full parent name with the command name as well.
        For example, in ``?one two three`` the qualified name would be
        ``one two three``.
        """

        parent = self.full_parent_name
        if parent:
            return parent + " " + self.name
        return self.name

    def get_command(self, name: str):
        return self._commands.get(name)

    @property
    def commands(self):
        return self._commands.values()

    def add_command(self, command: Type[Self]):
        self._commands[command.qualified_name] = command
        return command

    def remove_command(self, name: str):
        return self._commands.pop(name, None)

    def subcommand(self, *, cls: Type[Self] = None, **attrs: Any):
        if cls is None:
            cls = type(self)

            def decorator(func: Callable[..., T]) -> Callable[..., T]:
                if isinstance(func, SquidCommand):
                    raise TypeError("Callback is already a command.")

                attrs.setdefault("name", func.__name__)
                attrs["parent"] = self

                obj = cls(func, **attrs)
                self.add_command(obj)
                return functools.wraps(func)(obj)

        return decorator

    def __str__(self) -> str:
        return self.qualified_name


def command(
    *,
    cls: Type[SquidCommand] = None,
    **attrs: Any,
):
    """A decorator that transforms a function into a :class:`Command`
    subclass under the name ``name``. The ``cls`` argument is the
    type of :class:`Command` to use under the hood. If not
    provided, then the :class:`Command` class is used. If a keyword
    argument is provided then its value is forwarded to the
    :class:`Command` class constructor.
    Parameters
    -----------
    name: :class:`str`
        The name to give the command. This is the name that is used to
        invoke it via the command line.
    cls
        The type of command to create. Defaults to :class:`Command`.
    attrs
        Keyword arguments to pass into the construction of the command.
    Example
    --------
    .. code-block:: python3
        @command()
        def greet(ctx):
            ctx.send('Hello!')
    """

    if cls is None:
        cls = SquidCommand

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if isinstance(func, SquidCommand):
            raise TypeError("Callback is already a command.")

        attrs.setdefault("name", func.__name__)
        return functools.wraps(func)(cls(func, **attrs))

    return decorator
