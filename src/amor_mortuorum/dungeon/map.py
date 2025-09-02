from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TileType(Enum):
    WALL = 0
    FLOOR = 1
    DOOR = 2
    STAIRS_DOWN = 3


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def right(self) -> int:
        return self.x + self.w

    def bottom(self) -> int:
        return self.y + self.h

    def center(self) -> Point:
        return Point(self.x + self.w // 2, self.y + self.h // 2)

    def contains(self, p: Point) -> bool:
        return (self.x <= p.x < self.right()) and (self.y <= p.y < self.bottom())


class DungeonMap:
    """
    The core tile map abstraction. Provides safety checks, carving helpers, and
    query methods used by generation and movement. All tile access is bounds-
    checked to prevent out-of-bounds errors.
    """

    def __init__(self, width: int, height: int, default: TileType = TileType.WALL) -> None:
        if width < 3 or height < 3:
            raise ValueError("Map must be at least 3x3 to maintain wall borders")
        self.width = width
        self.height = height
        self._tiles: List[List[TileType]] = [
            [default for _ in range(width)] for _ in range(height)
        ]
        # Optional metadata markers
        self.start: Optional[Point] = None
        self.stairs_down: Optional[Point] = None

    # ---- Safety / Bounds -------------------------------------------------
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> TileType:
        if not self.in_bounds(x, y):
            raise IndexError(f"Tile out of bounds: ({x},{y}) not in [0,{self.width})x[0,{self.height})")
        return self._tiles[y][x]

    def set_tile(self, x: int, y: int, t: TileType) -> None:
        if not self.in_bounds(x, y):
            # Guard and log rather than throw in generation; corridors/rooms never
            # attempt to write OOB, but this protects against future regressions.
            logger.error("Attempt to write out-of-bounds tile at (%d,%d)", x, y)
            return
        self._tiles[y][x] = t

    # ---- Query -----------------------------------------------------------
    def is_walkable(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        t = self._tiles[y][x]
        return t in (TileType.FLOOR, TileType.DOOR, TileType.STAIRS_DOWN)

    def neighbors_4(self, x: int, y: int) -> Iterable[Point]:
        # Ordered for deterministic traversal
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield Point(nx, ny)

    # ---- Carving helpers -------------------------------------------------
    def carve_room(self, rect: Rect) -> None:
        for yy in range(rect.y, rect.bottom()):
            for xx in range(rect.x, rect.right()):
                self.set_tile(xx, yy, TileType.FLOOR)

    def carve_h_corridor(self, x1: int, x2: int, y: int) -> None:
        if x2 < x1:
            x1, x2 = x2, x1
        for xx in range(x1, x2 + 1):
            self.set_tile(xx, y, TileType.FLOOR)

    def carve_v_corridor(self, y1: int, y2: int, x: int) -> None:
        if y2 < y1:
            y1, y2 = y2, y1
        for yy in range(y1, y2 + 1):
            self.set_tile(x, yy, TileType.FLOOR)

    # ---- Search ----------------------------------------------------------
    def bfs_distance_map(self, start: Point) -> List[List[Optional[int]]]:
        """
        Compute BFS distances from start to all reachable tiles.
        Returns 2D list of distances or None for unreachable.
        Deterministic neighbor ordering.
        """
        dist: List[List[Optional[int]]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        if not self.in_bounds(start.x, start.y):
            return dist
        if not self.is_walkable(start.x, start.y):
            return dist
        from collections import deque

        dq = deque()
        dq.append(start)
        dist[start.y][start.x] = 0
        while dq:
            p = dq.popleft()
            d = dist[p.y][p.x]
            for n in self.neighbors_4(p.x, p.y):
                if dist[n.y][n.x] is not None:
                    continue
                if not self.is_walkable(n.x, n.y):
                    continue
                dist[n.y][n.x] = d + 1 if d is not None else 0
                dq.append(n)
        return dist

    def farthest_reachable(self, start: Point) -> Optional[Point]:
        dist = self.bfs_distance_map(start)
        max_d = -1
        far: Optional[Point] = None
        for y in range(self.height):
            for x in range(self.width):
                d = dist[y][x]
                if d is None:
                    continue
                if d > max_d:
                    max_d = d
                    far = Point(x, y)
        return far

    # ---- Export / Compare -----------------------------------------------
    def to_str_lines(self) -> List[str]:
        symbol = {
            TileType.WALL: '#',
            TileType.FLOOR: '.',
            TileType.DOOR: '+',
            TileType.STAIRS_DOWN: '>'
        }
        lines: List[str] = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                if self.start and self.start.x == x and self.start.y == y:
                    row.append('@')
                else:
                    row.append(symbol[self._tiles[y][x]])
            lines.append(''.join(row))
        return lines

    def snapshot(self) -> Tuple[Tuple[int, ...], ...]:
        """
        Deterministic, hashable snapshot of the tiles for equality tests.
        """
        return tuple(tuple(self._tiles[y][x].value for x in range(self.width)) for y in range(self.height))
