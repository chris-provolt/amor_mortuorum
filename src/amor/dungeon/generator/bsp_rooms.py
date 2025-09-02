from __future__ import annotations
import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..tiles import MapGrid, Tile

logger = logging.getLogger(__name__)


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def intersects(self, other: "Rect", padding: int = 1) -> bool:
        return not (
            self.x + self.w + padding <= other.x
            or other.x + other.w + padding <= self.x
            or self.y + self.h + padding <= other.y
            or other.y + other.h + padding <= self.y
        )


class RoomsGenerator:
    """Rooms + corridors generator (BSP-like), robust and navigable.

    This algorithm attempts to place a number of non-overlapping rectangular rooms
    and connects them with L-shaped corridors in order of their centers.
    """

    def __init__(
        self,
        max_rooms: int = 18,
        room_min_size: int = 4,
        room_max_size: int = 10,
    ) -> None:
        self.max_rooms = max_rooms
        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

    def generate(self, width: int, height: int, seed: Optional[int] = None) -> MapGrid:
        rng = random.Random(seed)
        tiles = [[Tile.WALL for _ in range(width)] for _ in range(height)]

        rooms: List[Rect] = []
        attempts = 0
        max_attempts = self.max_rooms * 10
        while len(rooms) < self.max_rooms and attempts < max_attempts:
            w = rng.randint(self.room_min_size, self.room_max_size)
            h = rng.randint(self.room_min_size, self.room_max_size)
            x = rng.randint(1, max(1, width - w - 2))
            y = rng.randint(1, max(1, height - h - 2))
            new_room = Rect(x, y, w, h)
            if any(new_room.intersects(other, padding=1) for other in rooms):
                attempts += 1
                continue
            self._carve_room(tiles, new_room)
            rooms.append(new_room)
            attempts += 1

        if not rooms:
            # Ensure at least one open area
            center_room = Rect(width // 4, height // 4, width // 2, height // 2)
            self._carve_room(tiles, center_room)
            rooms.append(center_room)

        # Sort by center for a simple connection scheme
        rooms.sort(key=lambda r: (r.center()[0], r.center()[1]))
        for i in range(1, len(rooms)):
            x1, y1 = rooms[i - 1].center()
            x2, y2 = rooms[i].center()
            if rng.random() < 0.5:
                self._carve_h_corridor(tiles, x1, x2, y1)
                self._carve_v_corridor(tiles, y1, y2, x2)
            else:
                self._carve_v_corridor(tiles, y1, y2, x1)
                self._carve_h_corridor(tiles, x1, x2, y2)

        # Entrance at first room center, exit at farthest room center
        entrance = rooms[0].center()
        exit_pos = max((r.center() for r in rooms), key=lambda c: (c[0] - entrance[0]) ** 2 + (c[1] - entrance[1]) ** 2)

        # Ensure bounds are walls
        self._frame_walls(tiles)

        logger.debug("RoomsGenerator: generated %d rooms", len(rooms))
        return MapGrid(width, height, tiles, entrance, exit_pos)

    @staticmethod
    def _carve_room(tiles: List[List[Tile]], room: Rect) -> None:
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                tiles[y][x] = Tile.FLOOR

    @staticmethod
    def _carve_h_corridor(tiles: List[List[Tile]], x1: int, x2: int, y: int) -> None:
        if x2 < x1:
            x1, x2 = x2, x1
        for x in range(x1, x2 + 1):
            tiles[y][x] = Tile.FLOOR

    @staticmethod
    def _carve_v_corridor(tiles: List[List[Tile]], y1: int, y2: int, x: int) -> None:
        if y2 < y1:
            y1, y2 = y2, y1
        for y in range(y1, y2 + 1):
            tiles[y][x] = Tile.FLOOR

    @staticmethod
    def _frame_walls(tiles: List[List[Tile]]) -> None:
        h = len(tiles)
        w = len(tiles[0]) if h else 0
        for x in range(w):
            tiles[0][x] = Tile.WALL
            tiles[h - 1][x] = Tile.WALL
        for y in range(h):
            tiles[y][0] = Tile.WALL
            tiles[y][w - 1] = Tile.WALL
