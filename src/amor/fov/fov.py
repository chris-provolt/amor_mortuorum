from __future__ import annotations

from typing import Iterable, List, Set, Tuple
import logging

from amor.map.grid import MapGrid

logger = logging.getLogger(__name__)

Coord = Tuple[int, int]


def chebyshev_distance(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> List[Coord]:
    """
    Bresenham's line algorithm. Returns the list of points from (x0, y0) to (x1, y1) inclusive.
    """
    points: List[Coord] = []

    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy

    return points


def is_visible_line(grid: MapGrid, x0: int, y0: int, x1: int, y1: int, *, include_opaque_target: bool = True) -> bool:
    """
    Checks line of sight between (x0, y0) and (x1, y1) on the grid.

    include_opaque_target=True means the final target tile is allowed to be opaque.
    All intermediate tiles must be transparent; if any is opaque, LoS is blocked.
    """
    if not grid.is_in_bounds(x0, y0) or not grid.is_in_bounds(x1, y1):
        return False

    line = bresenham_line(x0, y0, x1, y1)
    if not line:
        return False

    # Skip checking the first tile (origin) and optionally the last (target)
    end_index = len(line) - (1 if include_opaque_target else 0)
    for idx, (x, y) in enumerate(line):
        if idx == 0:
            continue
        if idx >= end_index:
            break
        if not grid.is_transparent(x, y):
            logger.debug("LoS blocked at (%d,%d) between (%d,%d)->(%d,%d)", x, y, x0, y0, x1, y1)
            return False
    return True


def compute_fov(grid: MapGrid, origin: Coord, radius: int, *, include_opaque_targets: bool = True) -> Set[Coord]:
    """
    Compute the set of visible tiles from origin within Chebyshev radius using line-of-sight.

    Simpler than symmetric shadowcasting but correct for typical roguelike needs.
    Returns a set of (x, y) coordinates that are visible. The origin is always visible.
    """
    ox, oy = origin
    if not grid.is_in_bounds(ox, oy):
        raise ValueError("Origin out of bounds")
    if radius < 0:
        raise ValueError("radius must be >= 0")

    visible: Set[Coord] = set()
    visible.add((ox, oy))

    min_x = max(0, ox - radius)
    max_x = min(grid.width - 1, ox + radius)
    min_y = max(0, oy - radius)
    max_y = min(grid.height - 1, oy + radius)

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if x == ox and y == oy:
                continue
            if chebyshev_distance(ox, oy, x, y) <= radius:
                if is_visible_line(grid, ox, oy, x, y, include_opaque_target=include_opaque_targets):
                    visible.add((x, y))

    logger.debug("FOV from (%d,%d) radius %d -> %d visible tiles", ox, oy, radius, len(visible))
    return visible
