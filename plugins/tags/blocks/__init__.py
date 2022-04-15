from .command import CommandBlock, OverrideBlock
from .cooldown import CooldownBlock
from .hidden import HiddenBlock
from .react import ReactBlock
from .redirect import RedirectBlock
from .require_blacklist import RequireBlock, BlacklistBlock
from .silent import SilentBlock

stable_blocks = [
    CommandBlock(),
    OverrideBlock(),
    CooldownBlock(),
    HiddenBlock(),
    ReactBlock(),
    RedirectBlock(),
    RequireBlock(),
    BlacklistBlock(),
    SilentBlock(),
]
