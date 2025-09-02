from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set

from ..rng import RNGManager

logger = logging.getLogger(__name__)


Tile = str  # '#' for wall, '.' for floor, 'C' for chest marker (not required in grid)
Point = Tuple[int, int]


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    grid: Tuple[str, ...]  # Tuple of strings, each string is a row
    chests: Tuple[Point, ...]  # Coordinates of chests (x, y)

    def signature(self) -> str:
        """Deterministic signature of layout content (grid + chest coords)."""
        payload = {
            "w": self.width,
            "h": self.height,
            "grid": list(self.grid),
            "chests": list(self.chests),
        }
        raw = str(payload).encode("utf-8")
        h = hashlib.blake2b(raw, digest_size=16)
        return h.hexdigest()


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    def center(self) -> Point:
        cx = self.x + self.w // 2
        cy = self.y + self.h // 2
        return (cx, cy)

    def tiles(self) -> List[Point]:
        return [(x, y) for x in range(self.x, self.x + self.w) for y in range(self.y, self.y + self.h)]


class DungeonGenerator:
    """Deterministic dungeon floor generator.

    Uses a simple rooms-and-corridors algorithm seeded per floor via RNGManager.
    Chest positions are selected deterministically using the same floor RNG, so that
    both layout and chest placements are reproducible given (seed, floor).
    """

    def __init__(self, rngm: RNGManager, width: int = 64, height: int = 64) -> None:
        self.rngm = rngm
        self.width = width
        self.height = height

    def generate(self, floor: int) -> Layout:
        rng = self.rngm.context_rng("floor_layout", floor)
        logger.debug("Generating floor %d with derived RNG", floor)
        # Initialize grid with walls
        grid = [["#" for _ in range(self.height)] for _ in range(self.width)]

        # Determine number of rooms
        room_count = 8 + rng.randint(0, 7)  # 8..15
        rooms: List[Room] = []

        for _ in range(room_count):
            w = rng.randint(4, 10)
            h = rng.randint(4, 10)
            # Keep a margin of 1 tile
            x = rng.randint(1, max(1, self.width - w - 2))
            y = rng.randint(1, max(1, self.height - h - 2))
            rooms.append(Room(x, y, w, h))

        # Carve rooms
        for r in rooms:
            for x in range(r.x, min(self.width - 1, r.x + r.w)):
                for y in range(r.y, min(self.height - 1, r.y + r.h)):
                    grid[x][y] = "."

        # Connect rooms in order of x by L-shaped corridors
        rooms_sorted = sorted(rooms, key=lambda r: r.x)
        for i in range(1, len(rooms_sorted)):
            a = rooms_sorted[i - 1].center()
            b = rooms_sorted[i].center()
            self._carve_corridor(grid, a, b)

        # Place chests deterministically using the same floor rng
        floor_chests: Set[Point] = set()
        for r in rooms:
            # 50% chance to place a chest in this room
            if rng.random() < 0.5:
                # Try up to 10 times to find a floor tile within the room
                placed = False
                for _ in range(10):
                    cx = rng.randint(r.x, min(self.width - 2, r.x + r.w - 1))
                    cy = rng.randint(r.y, min(self.height - 2, r.y + r.h - 1))
                    if grid[cx][cy] == ".":
                        floor_chests.add((cx, cy))
                        placed = True
                        break
                if not placed:
                    # Fallback: center of room
                    floor_chests.add(r.center())

        # Prepare immutable representation
        rows: List[str] = []
        for y in range(self.height):
            row_chars = [grid[x][y] for x in range(self.width)]
            rows.append("".join(row_chars))

        layout = Layout(
            width=self.width,
            height=self.height,
            grid=tuple(rows),
            chests=tuple(sorted(floor_chests)),
        )
        logger.debug("Generated layout signature: %s, chests=%d", layout.signature(), len(layout.chests))
        return layout

    def _carve_corridor(self, grid: List[List[Tile]], a: Point, b: Point) -> None:
        ax, ay = a
        bx, by = b
        # Horizontal first, then vertical
        x_step = 1 if bx >= ax else -1
        for x in range(ax, bx + x_step, x_step):
            if 0 <= x < self.width and 0 <= ay < self.height:
                grid[x][ay] = "."
        y_step = 1 if by >= ay else -1
        for y in range(ay, by + y_step, y_step):
            if 0 <= bx < self.width and 0 <= y < self.height:
                grid[bx][y] = "."
