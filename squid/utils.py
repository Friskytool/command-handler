import re
import sys
from datetime import datetime, timedelta
import time
from typing import TYPE_CHECKING, Any, Dict, ForwardRef, Iterable, Literal, Tuple, Union
import datetime

if TYPE_CHECKING:
    from squid.bot.context import CommandContext

from squid.bot.errors import CheckFailure

PY_310 = sys.version_info >= (3, 10)


def has_role(ctx: "CommandContext"):
    roles = ctx.setting("roles")
    print("roles:", roles)
    if roles and not any(r["id"] in ctx.author.roles for r in roles):
        raise CheckFailure(
            "Missing Roles\n" + "\n".join([f"- {i['name']}" for i in roles]),
            fmt="diff",
        )
    return True


def format_list(l: list):
    if len(l) == 0:
        return ""
    elif len(l) == 1:
        return str(l[0])
    elif len(l) == 2:
        return "{} and {}".format(l[0], l[1])
    else:
        return ", ".join(l[:-1]) + " and " + l[-1]


def s(o):
    return "" if o == 1 else "s"


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def discord_timestamp(t):
    return datetime.datetime.utcfromtimestamp(time.mktime(t.timetuple())) - timedelta(
        hours=12
    )


# camel case to snake case
def camel_to_snake(name: str) -> str:
    """Converts a camel case string to snake case.

    Args:
        name (str): The camel case string to convert.

    Returns:
        str: The snake case string.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


intervals = (
    ("weeks", 604800),  # 60 * 60 * 24 * 7
    ("days", 86400),  # 60 * 60 * 24
    ("hours", 3600),  # 60 * 60
    ("minutes", 60),
    ("seconds", 1),
)


def display_time(seconds, *, granularity=10, wrap="**"):
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()
    result = []
    base = f"{wrap}{{0}}{wrap} {{1}}"
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            text = base.format(int(value), name)
            result.append(text)
    return ", ".join(result[:granularity])


def flatten_literal_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    params = []
    literal_cls = type(Literal[0])
    for p in parameters:
        if isinstance(p, literal_cls):
            params.extend(p.__args__)
        else:
            params.append(p)
    return tuple(params)


def normalise_optional_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    none_cls = type(None)
    return tuple(p for p in parameters if p is not none_cls) + (none_cls,)


def evaluate_annotation(
    tp: Any,
    globals: Dict[str, Any],
    locals: Dict[str, Any],
    cache: Dict[str, Any],
    *,
    implicit_str: bool = True,
):
    if isinstance(tp, ForwardRef):
        tp = tp.__forward_arg__
        # ForwardRefs always evaluate their internals
        implicit_str = True

    if implicit_str and isinstance(tp, str):
        if tp in cache:
            return cache[tp]
        evaluated = eval(tp, globals, locals)
        cache[tp] = evaluated
        return evaluate_annotation(evaluated, globals, locals, cache)

    if hasattr(tp, "__args__"):
        implicit_str = True
        is_literal = False
        args = tp.__args__
        if not hasattr(tp, "__origin__"):
            if PY_310 and tp.__class__ is types.UnionType:  # type: ignore
                converted = Union[args]  # type: ignore
                return evaluate_annotation(converted, globals, locals, cache)

            return tp
        if tp.__origin__ is Union:
            try:
                if args.index(type(None)) != len(args) - 1:
                    args = normalise_optional_params(tp.__args__)
            except ValueError:
                pass
        if tp.__origin__ is Literal:
            if not PY_310:
                args = flatten_literal_params(tp.__args__)
            implicit_str = False
            is_literal = True

        evaluated_args = tuple(
            evaluate_annotation(arg, globals, locals, cache, implicit_str=implicit_str)
            for arg in args
        )

        if is_literal and not all(
            isinstance(x, (str, int, bool, type(None))) for x in evaluated_args
        ):
            raise TypeError(
                "Literal arguments must be of type str, int, bool, or NoneType."
            )

        if evaluated_args == args:
            return tp

        try:
            return tp.copy_with(evaluated_args)
        except AttributeError:
            return tp.__origin__[evaluated_args]

    return


regex = re.compile(
    r"^((?P<weeks>[\.\d]+?)w)?((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$"
)


def parse_time(time_str):
    """
    Parse a time string e.g. (2h13m) into a timedelta object.

    Modified from virhilo's answer at https://stackoverflow.com/a/4628148/851699

    :param time_str: A string identifying a duration.  (eg. 2h13m)
    :return datetime.timedelta: A datetime.timedelta object
    """
    if time_str.isdigit():
        time_str += "s"
        
    parts = regex.match(time_str)
    assert (
        parts is not None
    ), "Could not parse any time information from '{}'.  Examples of valid strings: '8h', '2d8h5m20s', '2m4s'".format(
        time_str
    )
    time_params = {
        name: float(param) for name, param in parts.groupdict().items() if param
    }

    return timedelta(**time_params)
