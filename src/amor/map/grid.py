from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Size:
    width: int
    height: int


class MapGrid:
    """
    A simple, engine-agnostic grid that tracks tile transparency for FOV.

    - True in `transparent[y][x]` means light/vision can pass through the tile.
    - False means the tile blocks vision (e.g., walls).

    Coordinate system is 0-based: x in [0, width), y in [0, height).
    """

    def __init__(self, width: int, height: int, default_transparent: bool = True) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("MapGrid width/height must be > 0")
        self._size = Size(width, height)
        self._transparent: List[List[bool]] = [
            [default_transparent for _ in range(width)] for _ in range(height)
        ]
        logger.debug("MapGrid created: %dx%d, default_transparent=%s", width, height, default_transparent)

    @property
    def size(self) -> Size:
        return self._size

    @property
    def width(self) -> int:
        return self._size.width

    @property
    def height(self) -> int:
        return self._size.height

    def is_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_transparent(self, x: int, y: int) -> bool:
        if not self.is_in_bounds(x, y):
            return False
        return self._transparent[y][x]

    def set_transparent(self, x: int, y: int, transparent: bool) -> None:
        if not self.is_in_bounds(x, y):
            raise IndexError("Tile out of bounds")
        self._transparent[y][x] = bool(transparent)
        logger.debug("Tile (%d,%d) transparency set to %s", x, y, transparent)

    def fill_transparent(self, value: bool) -> None:
        for y in range(self.height):
            row = self._transparent[y]
            for x in range(self.width):
                row[x] = value
        logger.debug("MapGrid all tiles transparency set to %s", value)

    @classmethod
    def from_ascii(cls, rows: Sequence[str], wall_chars: Iterable[str] = ("#",)) -> "MapGrid":
        """
        Build a MapGrid from ASCII rows for tests/tools.
        - Any char in wall_chars is considered opaque (transparent=False).
        - All others are transparent.
        """
        if not rows:
            raise ValueError("rows must not be empty")
        height = len(rows)
        width = len(rows[0])
        for r in rows:
            if len(r) != width:
                raise ValueError("All rows must be same width")
        grid = cls(width, height, default_transparent=True)
        wall_set = set(wall_chars)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                grid.set_transparent(x, y, ch not in wall_set)
        return grid

    def clone(self) -> "MapGrid":
        clone = MapGrid(self.width, self.height, default_transparent=True)
        for y in range(self.height):
            for x in range(self.width):
                clone.set_transparent(x, y, self._transparent[y][x])
        return clone

    def __repr__(self) -> str:
        return f"MapGrid({self.width}x{self.height})"
