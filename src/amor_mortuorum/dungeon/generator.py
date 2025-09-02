from __future__ import annotations

import logging
import random
from typing import Optional, Tuple

from .map import DungeonMap
from .tiles import TileType

logger = logging.getLogger(__name__)


class DungeonGenerator:
    """Deterministic floor generator.

    This implementation is deliberately simple for early milestones:
    - Solid wall border
    - Open interior floor
    - Spawn at (1, 1)
    - Stairs at (width-2, height-2)

    The generator accepts an optional seed; each call to generate() can be
    further varied by the floor number for deterministic runs across floors.
    """

    def __init__(self, seed: Optional[int] = None):
        self._base_seed = seed

    def generate(self, floor: int, width: int = 32, height: int = 18) -> DungeonMap:
        logger.info("Generating floor %d (%dx%d)", floor, width, height)
        m = DungeonMap(width, height, default_tile=TileType.WALL)

        # Carve out an open interior rectangle
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                m.set(x, y, TileType.FLOOR)

        # Use a local RNG if seed provided (kept for future variance)
        if self._base_seed is not None:
            rng = random.Random((self._base_seed, floor))
        else:
            rng = random.Random()
        rng.seed((self._base_seed, floor)) if self._base_seed is not None else None

        # For now, keep deterministic positions for clarity & tests.
        spawn_x, spawn_y = 1, 1
        stairs_x, stairs_y = width - 2, height - 2

        # Place features
        m.set(spawn_x, spawn_y, TileType.FLOOR)
        m.set(stairs_x, stairs_y, TileType.STAIRS_DOWN)

        # Record meta
        m.set_spawn(spawn_x, spawn_y)
        m.set_stairs_down(stairs_x, stairs_y)

        logger.debug("Generated map:\n%s", str(m))
        return m
