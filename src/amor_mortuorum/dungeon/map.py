from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .tiles import TileType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class DungeonMap:
    """A 2D tile-grid representing a single dungeon floor.

    Attributes:
        width: Grid width in tiles
        height: Grid height in tiles
        grid: 2D list [y][x] of TileType
        spawn: Player spawn coordinate on this floor
        stairs_down: Coordinate of stairs leading to the next floor
    """

    def __init__(self, width: int, height: int, default_tile: TileType = TileType.WALL):
        if width < 3 or height < 3:
            raise ValueError("Map must be at least 3x3 to allow walls + interior")
        self.width = width
        self.height = height
        self.grid: List[List[TileType]] = [[default_tile for _ in range(width)] for _ in range(height)]
        self.spawn: Optional[Point] = None
        self.stairs_down: Optional[Point] = None
        logger.debug("Initialized DungeonMap %dx%d with default %s", width, height, default_tile)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> TileType:
        if not self.in_bounds(x, y):
            raise IndexError(f"Coordinates out of bounds: {(x, y)}")
        return self.grid[y][x]

    def set(self, x: int, y: int, tile: TileType) -> None:
        if not self.in_bounds(x, y):
            raise IndexError(f"Coordinates out of bounds: {(x, y)}")
        self.grid[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        return self.get(x, y).is_walkable

    def set_spawn(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise IndexError(f"Spawn out of bounds: {(x, y)}")
        if not self.get(x, y).is_walkable:
            raise ValueError("Spawn must be placed on a walkable tile")
        self.spawn = Point(x, y)
        logger.debug("Set spawn at %s", self.spawn)

    def set_stairs_down(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise IndexError(f"Stairs out of bounds: {(x, y)}")
        if not self.get(x, y).is_walkable:
            raise ValueError("Stairs must be placed on a walkable tile")
        self.stairs_down = Point(x, y)
        logger.debug("Set stairs_down at %s", self.stairs_down)

    def __str__(self) -> str:
        """Return a simple ASCII representation for debugging."""
        lines = []
        for y in range(self.height):
            lines.append(''.join(self.grid[y][x].glyph for x in range(self.width)))
        return '\n'.join(lines)
