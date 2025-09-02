from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Set, Tuple
import logging

from amor.map.grid import MapGrid
from amor.fov.fov import compute_fov

logger = logging.getLogger(__name__)

Coord = Tuple[int, int]


class FogTileState(str, Enum):
    UNSEEN = "unseen"         # never seen; fully dark
    SEEN = "seen"             # seen before but not currently visible; dim
    VISIBLE = "visible"       # currently visible; full brightness


@dataclass
class FogSettings:
    vision_radius: int = 8
    dim_factor: float = 0.35  # brightness for seen-not-visible tiles

    def __post_init__(self) -> None:
        if self.vision_radius < 0:
            raise ValueError("vision_radius must be >= 0")
        if not (0.0 <= self.dim_factor <= 1.0):
            raise ValueError("dim_factor must be between 0.0 and 1.0")


class FogOfWar:
    """
    Manages visibility and memory (auto-map) over a MapGrid.

    Responsibilities:
    - Calculates current visible tiles (FOV) around the player.
    - Remembers tiles that have been seen at least once.
    - Provides tile state (unseen/seen/visible) and a light map for rendering.

    This class is engine-agnostic; use its outputs in your renderer to apply
    shading:
      - UNSEEN: brightness 0.0
      - SEEN: brightness = dim_factor
      - VISIBLE: brightness 1.0
    """

    def __init__(self, grid: MapGrid, settings: Optional[FogSettings] = None) -> None:
        self.grid = grid
        self.settings = settings or FogSettings()
        self._seen: List[List[bool]] = [[False for _ in range(grid.width)] for _ in range(grid.height)]
        self._visible: Set[Coord] = set()
        logger.debug(
            "FogOfWar initialized: %dx%d radius=%d dim=%.2f",
            grid.width,
            grid.height,
            self.settings.vision_radius,
            self.settings.dim_factor,
        )

    def reset_memory(self) -> None:
        """Forget all seen tiles (e.g., on new floor)."""
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                self._seen[y][x] = False
        logger.debug("FogOfWar memory reset")

    def mark_all_seen(self) -> None:
        """Debug/cheat: mark the whole map as seen."""
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                self._seen[y][x] = True
        logger.debug("FogOfWar marked all tiles as seen")

    def update(self, player_pos: Coord, *, radius: Optional[int] = None) -> None:
        """
        Recompute current visibility and update memory around the player.

        - player_pos: (x, y) position of the player.
        - radius: optional override for vision radius; if None, uses settings.
        """
        if not self.grid.is_in_bounds(*player_pos):
            raise ValueError("player_pos out of bounds")

        use_radius = self.settings.vision_radius if radius is None else radius
        if use_radius < 0:
            raise ValueError("radius must be >= 0")

        self._visible = compute_fov(self.grid, player_pos, use_radius, include_opaque_targets=True)

        # Update memory for anything currently visible
        for (x, y) in self._visible:
            self._seen[y][x] = True

        logger.debug("FogOfWar updated at %s with radius %d; %d visible tiles", player_pos, use_radius, len(self._visible))

    def get_state(self, x: int, y: int) -> FogTileState:
        if not self.grid.is_in_bounds(x, y):
            raise IndexError("Tile out of bounds")
        if (x, y) in self._visible:
            return FogTileState.VISIBLE
        if self._seen[y][x]:
            return FogTileState.SEEN
        return FogTileState.UNSEEN

    def light_map(self) -> List[List[float]]:
        """
        Returns a matrix [height][width] of brightness multipliers suitable for rendering.
        0.0 for unseen, dim_factor for seen-not-visible, 1.0 for visible.
        """
        h, w = self.grid.height, self.grid.width
        dim = self.settings.dim_factor
        result: List[List[float]] = [[0.0 for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                if (x, y) in self._visible:
                    result[y][x] = 1.0
                elif self._seen[y][x]:
                    result[y][x] = dim
                else:
                    result[y][x] = 0.0
        return result

    def visible_tiles(self) -> Set[Coord]:
        return set(self._visible)

    def seen_mask(self) -> List[List[bool]]:
        return [row[:] for row in self._seen]

    def on_map_changed(self, new_grid: MapGrid) -> None:
        """
        Replace the underlying grid (e.g., when switching floors) and reset memory.
        """
        self.grid = new_grid
        self._seen = [[False for _ in range(new_grid.width)] for _ in range(new_grid.height)]
        self._visible.clear()
        logger.debug("FogOfWar map changed to %dx%d; memory cleared", new_grid.width, new_grid.height)
