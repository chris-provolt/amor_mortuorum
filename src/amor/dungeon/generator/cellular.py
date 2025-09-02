from __future__ import annotations
import logging
import random
from typing import Optional, Tuple

from ..tiles import MapGrid, Tile
from ..pathfinding import largest_connected_region

logger = logging.getLogger(__name__)


class CellularGenerator:
    """Cellular automata caverns generator.

    Algorithm:
    - Initialize grid with random walls based on initial probability.
    - Apply a number of smoothing steps using the 8-neighbor rule (>= threshold => wall).
    - Keep only the largest connected floor region (others become walls) to guarantee navigability.
    - Pick entrance and exit as far apart floor tiles as feasible.
    """

    def __init__(
        self,
        initial_wall_prob: float = 0.45,
        smooth_steps: int = 5,
        wall_threshold: int = 5,
        min_floor_fraction: float = 0.28,
    ) -> None:
        self.initial_wall_prob = float(initial_wall_prob)
        self.smooth_steps = int(smooth_steps)
        self.wall_threshold = int(wall_threshold)
        self.min_floor_fraction = float(min_floor_fraction)

    def generate(self, width: int, height: int, seed: Optional[int] = None) -> MapGrid:
        rng = random.Random(seed)

        tiles = [[Tile.WALL for _ in range(width)] for _ in range(height)]

        def randomize():
            for y in range(height):
                for x in range(width):
                    if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                        tiles[y][x] = Tile.WALL
                    else:
                        tiles[y][x] = Tile.WALL if rng.random() < self.initial_wall_prob else Tile.FLOOR

        def smooth():
            # Apply smoothing based on Moore neighborhood
            for _ in range(self.smooth_steps):
                new_tiles = [row[:] for row in tiles]
                for y in range(1, height - 1):
                    for x in range(1, width - 1):
                        wall_count = 0
                        for ny in (y - 1, y, y + 1):
                            for nx in (x - 1, x, x + 1):
                                if nx == x and ny == y:
                                    continue
                                if tiles[ny][nx] == Tile.WALL:
                                    wall_count += 1
                        new_tiles[y][x] = Tile.WALL if wall_count >= self.wall_threshold else Tile.FLOOR
                # keep borders walls
                for bx in range(width):
                    new_tiles[0][bx] = Tile.WALL
                    new_tiles[height - 1][bx] = Tile.WALL
                for by in range(height):
                    new_tiles[by][0] = Tile.WALL
                    new_tiles[by][width - 1] = Tile.WALL
                for y in range(height):
                    tiles[y] = new_tiles[y]

        # Try up to a few rerolls to satisfy min floor fraction
        for attempt in range(5):
            randomize()
            smooth()
            grid = MapGrid(width, height, tiles, (1, 1), (width - 2, height - 2))
            largest = largest_connected_region(grid)
            floor_cnt = len(largest)
            frac = floor_cnt / float(width * height)
            if frac >= self.min_floor_fraction:
                break
            if attempt == 4:
                logger.warning(
                    "CellularGenerator: min floor fraction not reached (%.2f < %.2f), proceeding",
                    frac,
                    self.min_floor_fraction,
                )

        # Keep only largest connected region as floors, rest walls
        largest = largest_connected_region(grid)
        for y in range(height):
            for x in range(width):
                grid.tiles[y][x] = Tile.FLOOR if (x, y) in largest else Tile.WALL

        # Choose entrance/exit as far apart points in the region
        entrance, exit_pos = self._pick_farthest_points(grid, rng)
        grid.entrance = entrance
        grid.exit = exit_pos

        return grid

    @staticmethod
    def _pick_farthest_points(grid: MapGrid, rng: random.Random) -> Tuple[tuple[int, int], tuple[int, int]]:
        # Collect floor positions
        floors = [(x, y) for y in range(grid.height) for x in range(grid.width) if grid.tiles[y][x] == Tile.FLOOR]
        if not floors:
            # Fallback to center if something went wrong
            c = (grid.width // 2, grid.height // 2)
            return c, c
        start = rng.choice(floors)
        # BFS to find farthest from start
        from collections import deque

        def bfs_far(p: tuple[int, int]) -> tuple[tuple[int, int], int]:
            q = deque([p])
            dist = {p: 0}
            far = (p, 0)
            while q:
                x, y = q.popleft()
                d = dist[(x, y)]
                if d > far[1]:
                    far = ((x, y), d)
                for nx, ny in grid.neighbors4(x, y):
                    if (nx, ny) not in dist and grid.is_floor(nx, ny):
                        dist[(nx, ny)] = d + 1
                        q.append((nx, ny))
            return far

        a, _ = bfs_far(start)
        b, _ = bfs_far(a)
        return a, b
