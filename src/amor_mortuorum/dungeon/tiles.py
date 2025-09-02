from enum import Enum, auto
from typing import Tuple


class TileType(Enum):
    """Basic dungeon tile types.

    - WALL: Non-walkable obstacle
    - FLOOR: Walkable open tile
    - STAIRS_DOWN: Walkable tile that triggers floor descent
    """

    WALL = auto()
    FLOOR = auto()
    STAIRS_DOWN = auto()

    @property
    def is_walkable(self) -> bool:
        return self in {TileType.FLOOR, TileType.STAIRS_DOWN}

    @property
    def is_stairs_down(self) -> bool:
        return self is TileType.STAIRS_DOWN

    @property
    def glyph(self) -> str:
        """A single-character visualization useful for logs/debug.
        Not used by Arcade renderer, but handy for testing/logs.
        """
        return {TileType.WALL: '#', TileType.FLOOR: '.', TileType.STAIRS_DOWN: '>'}[self]

    @property
    def color(self) -> Tuple[int, int, int]:
        """Default RGB color for 2D rendering (Arcade), if desired."""
        return {
            TileType.WALL: (40, 40, 48),
            TileType.FLOOR: (180, 180, 180),
            TileType.STAIRS_DOWN: (200, 160, 40),
        }[self]
