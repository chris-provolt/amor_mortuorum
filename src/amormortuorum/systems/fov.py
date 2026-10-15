"""Field of view (recursive shadowcasting) and explored-tile memory.

Pure Python. Walls and locked doors block sight; floor and open doors do not.
Blocking tiles themselves are visible (so walls render at the edge of sight).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set

from .procgen import FloorMap, Pos, Tile

DEFAULT_FOV_RADIUS = 8

# Octant transforms for shadowcasting (xx, xy, yx, yy).
_OCTANTS = (
    (1, 0, 0, 1), (0, 1, 1, 0), (0, -1, 1, 0), (-1, 0, 0, 1),
    (-1, 0, 0, -1), (0, -1, -1, 0), (0, 1, -1, 0), (1, 0, 0, -1),
)


def is_transparent(fmap: FloorMap, x: int, y: int) -> bool:
    t = fmap.tile(x, y)
    if t == Tile.FLOOR:
        return True
    if t == Tile.DOOR:
        return not fmap.doors.get((x, y), False)
    return False


def compute_fov(fmap: FloorMap, origin: Pos, radius: int = DEFAULT_FOV_RADIUS) -> Set[Pos]:
    """Tiles visible from ``origin`` within ``radius`` (Euclidean), origin included."""
    ox, oy = origin
    visible: Set[Pos] = {origin}
    radius_sq = radius * radius

    def cast(row: int, start: float, end: float, xx: int, xy: int, yx: int, yy: int) -> None:
        if start < end:
            return
        for j in range(row, radius + 1):
            dx, dy = -j - 1, -j
            blocked_prev = False
            new_start = start
            while dx <= 0:
                dx += 1
                x = ox + dx * xx + dy * xy
                y = oy + dx * yx + dy * yy
                l_slope = (dx - 0.5) / (dy + 0.5)
                r_slope = (dx + 0.5) / (dy - 0.5)
                if start < r_slope:
                    continue
                if end > l_slope:
                    break
                if dx * dx + dy * dy <= radius_sq and fmap.in_bounds(x, y):
                    visible.add((x, y))
                opaque = not is_transparent(fmap, x, y)
                if blocked_prev:
                    if opaque:
                        new_start = r_slope
                        continue
                    blocked_prev = False
                    start = new_start
                elif opaque and j < radius:
                    blocked_prev = True
                    cast(j + 1, start, l_slope, xx, xy, yx, yy)
                    new_start = r_slope
            if blocked_prev:
                break

    for xx, xy, yx, yy in _OCTANTS:
        cast(1, 1.0, 0.0, xx, xy, yx, yy)
    return visible


@dataclass
class Visibility:
    """Current line of sight plus everything seen so far on this floor."""

    radius: int = DEFAULT_FOV_RADIUS
    visible: Set[Pos] = field(default_factory=set)
    explored: Set[Pos] = field(default_factory=set)

    def update(self, fmap: FloorMap, origin: Pos) -> Set[Pos]:
        """Recompute from ``origin``; return the tiles whose visibility changed."""
        new = compute_fov(fmap, origin, self.radius)
        changed = self.visible ^ new
        self.visible = new
        self.explored |= new
        return changed

    def state(self, pos: Pos) -> str:
        """``"visible"``, ``"explored"`` or ``"unknown"``."""
        if pos in self.visible:
            return "visible"
        if pos in self.explored:
            return "explored"
        return "unknown"


__all__ = ["DEFAULT_FOV_RADIUS", "is_transparent", "compute_fov", "Visibility"]
