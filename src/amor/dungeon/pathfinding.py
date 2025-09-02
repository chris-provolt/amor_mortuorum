from collections import deque
from typing import Optional, Tuple

from .tiles import MapGrid, Tile


def find_path_bfs(grid: MapGrid, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[int]:
    """Breadth-first search shortest path length on FLOORS; returns number of steps or None.

    Uses 4-directional movement.
    """
    if not grid.is_floor(*start) or not grid.is_floor(*goal):
        return None

    sx, sy = start
    gx, gy = goal
    q = deque([(sx, sy, 0)])
    seen = {start}
    while q:
        x, y, d = q.popleft()
        if (x, y) == (gx, gy):
            return d
        for nx, ny in grid.neighbors4(x, y):
            if (nx, ny) not in seen and grid.tiles[ny][nx] == Tile.FLOOR:
                seen.add((nx, ny))
                q.append((nx, ny, d + 1))
    return None


def largest_connected_region(grid: MapGrid) -> set[tuple[int, int]]:
    """Return set of coordinates belonging to the largest connected floor region (4-neigh)."""
    visited: set[tuple[int, int]] = set()
    best: set[tuple[int, int]] = set()
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.tiles[y][x] != Tile.FLOOR or (x, y) in visited:
                continue
            comp = set()
            q = deque([(x, y)])
            visited.add((x, y))
            while q:
                cx, cy = q.popleft()
                comp.add((cx, cy))
                for nx, ny in grid.neighbors4(cx, cy):
                    if (nx, ny) not in visited and grid.tiles[ny][nx] == Tile.FLOOR:
                        visited.add((nx, ny))
                        q.append((nx, ny))
            if len(comp) > len(best):
                best = comp
    return best
