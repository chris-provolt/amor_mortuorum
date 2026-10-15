"""
Amor Mortuorum: a dark roguelite built with Python + Arcade.

Layout:
- ``data``: static game content loaded from JSON (items, enemies, tables)
- ``systems``: pure-Python rules (procgen, combat, loot, run state, hub)
- ``persistence``: save files (meta progression + run state)
- ``core`` / ``scenes`` / ``ui``: the Arcade application layer

Importing this package does not import arcade.
"""
from importlib.metadata import PackageNotFoundError, version

from .errors import (
    AmorError,
    CryptFull,
    InsufficientGold,
    InvalidOperation,
    NotFound,
    OutOfStock,
)

__all__ = [
    "AmorError",
    "InsufficientGold",
    "OutOfStock",
    "CryptFull",
    "InvalidOperation",
    "NotFound",
    "__version__",
]

try:
    __version__ = version("amor-mortuorum")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
