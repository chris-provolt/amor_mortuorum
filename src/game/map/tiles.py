from __future__ import annotations

from enum import Enum
from typing import Set


class Tile(Enum):
    """Enumeration for tile types in the map grid.

    Use meaningful values rather than raw integers to avoid ambiguity and
    improve readability across the codebase.
    """

    FLOOR = 0
    WALL = 1
    VOID = 2  # Outside playable space, generally not placed inside actual grid


# Define which tiles are walkable. This makes it straightforward to extend later.
WALKABLE_TILES: Set[Tile] = {Tile.FLOOR}


def is_walkable_tile(tile: Tile) -> bool:
    """Return True if the provided tile type is walkable.

    Args:
        tile: A Tile enum member.

    Returns:
        bool: Whether the tile can be traversed by entities.
    """

    return tile in WALKABLE_TILES
