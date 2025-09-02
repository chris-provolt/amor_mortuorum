from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple


class Tile(IntEnum):
    WALL = 0
    FLOOR = 1


@dataclass
class MapGrid:
    """A simple tile grid with entrance/exit coordinates and helpers.

    Coordinates are (x, y) with (0,0) at top-left; x grows to the right, y grows down.
    """

    width: int
    height: int
    tiles: List[List[Tile]]  # tiles[y][x]
    entrance: Tuple[int, int]
    exit: Tuple[int, int]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_floor(self, x: int, y: int) -> bool:
        return self.tiles[y][x] == Tile.FLOOR

    def neighbors4(self, x: int, y: int):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def copy(self) -> "MapGrid":
        return MapGrid(
            self.width,
            self.height,
            [row[:] for row in self.tiles],
            self.entrance,
            self.exit,
        )
