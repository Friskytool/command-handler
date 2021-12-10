from functools import wraps
from ._types import _BaseCommand
from typing import Callable, Any, Optional, List, Union, Dict, Tuple, T, Type, TypeVar
import inspect
from .utils import evaluate_annotation
from .context import SquidContext
from .errors import ArgumentParsingError
from .converter import get_converter
import functools

CommandT = TypeVar("CommandT", bound="SquidCommand")


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

    def __init__(self, name, aliases, description, options):
        self.name = name
        self.aliases = aliases
        self.description = description
        self.options = options

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

    def update(self, **kwargs: Any) -> None:
        """Updates :class:`Command` instance with updated attribute.
        This works similarly to the :func:`.command` decorator in terms
        of parameters in that they are passed to the :class:`Command` or
        subclass constructors, sans the name and callback.
        """
        self.__init__(self.callback, **dict(self.__original_kwargs__, **kwargs))

    def __call__(self, context: SquidContext, *args, **kwargs) -> T:
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
        else:
            return self.callback(context, *args, **kwargs)  # type: ignore

    def transform(self, ctx: SquidContext, param: inspect.Parameter) -> Any:
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
                else:
                    raise exc
        view.previous = previous

        # type-checker fails to narrow argument
        return run_converters(ctx, converter, argument, param)  # type: ignore

    def _ensure_assignment_on_copy(self, other):

        # if I start adding checks they should be added here
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
        else:
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
        else:
            return self.name

    def __str__(self) -> str:
        return self.qualified_name


def command(
    *,
    name: str = None,
    cls: Type[SquidCommand] = None,
    **attrs: Any,
) -> Callable[[Type[SquidCommand]], Type[SquidCommand]]:
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
        return cls(func, **attrs)

    return decorator
