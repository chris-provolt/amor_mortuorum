from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Iterable, Set, Tuple
import logging

from .config import MINIMAP as MM_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class MinimapLayout:
    """Computed layout information for placing the minimap on screen."""

    origin_left: int
    origin_bottom: int
    pixel_width: int
    pixel_height: int
    tile_size: int


class MinimapModel:
    """Pure model that tracks explored tiles for the minimap.

    Keeps a set of explored (x, y) coordinates inside [0, width) x [0, height).
    """

    def __init__(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError("MinimapModel dimensions must be positive")
        self.width = width
        self.height = height
        self._explored: Set[Tuple[int, int]] = set()

    def reveal(self, x: int, y: int) -> bool:
        """Mark the tile as explored. Returns True if newly added, False if already explored.

        Out-of-bounds coordinates are ignored and return False.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            logger.debug("Attempt to reveal out-of-bounds tile (%s, %s)", x, y)
            return False
        before = len(self._explored)
        self._explored.add((x, y))
        return len(self._explored) > before

    def reveal_many(self, coords: Iterable[Tuple[int, int]]) -> int:
        """Reveal many tiles; returns the count of newly revealed tiles."""
        added = 0
        for x, y in coords:
            if self.reveal(x, y):
                added += 1
        return added

    def is_explored(self, x: int, y: int) -> bool:
        return (x, y) in self._explored

    def explored(self) -> Set[Tuple[int, int]]:
        return set(self._explored)

    def clear(self) -> None:
        self._explored.clear()


class MinimapRenderer:
    """Renderer/controller for the minimap overlay.

    Separates model (which is pure) from Arcade drawing & layout logic.
    """

    def __init__(self, model: MinimapModel):
        self.model = model
        self.enabled: bool = True
        self.layout: Optional[MinimapLayout] = None

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def resize(self, window_width: int, window_height: int) -> MinimapLayout:
        """Compute a new layout for the given window size and cache it."""
        margin = MM_CONFIG.margin_px
        # Available drawing area for the minimap (max constraints)
        max_w = max(1, int(window_width * MM_CONFIG.max_width_fraction) - margin * 2)
        max_h = max(1, int(window_height * MM_CONFIG.max_height_fraction) - margin * 2)

        # Compute a tile size that fits within the max area
        tile_size_w = max(1, max_w // self.model.width)
        tile_size_h = max(1, max_h // self.model.height)
        tile_size = max(1, min(tile_size_w, tile_size_h))

        pixel_w = min(max_w, self.model.width * tile_size)
        pixel_h = min(max_h, self.model.height * tile_size)

        # Anchor to top-right with margin; ensure on-screen even if too large
        origin_left = max(0, window_width - margin - pixel_w)
        origin_bottom = max(0, window_height - margin - pixel_h)

        self.layout = MinimapLayout(
            origin_left=origin_left,
            origin_bottom=origin_bottom,
            pixel_width=pixel_w,
            pixel_height=pixel_h,
            tile_size=tile_size,
        )
        logger.debug(
            "Minimap resized: layout=%s (window=%sx%s)",
            self.layout,
            window_width,
            window_height,
        )
        return self.layout

    def draw(
        self,
        player_pos: Optional[Tuple[int, int]] = None,
        is_room: Optional[Callable[[int, int], bool]] = None,
    ) -> None:
        """Draw the minimap if enabled.

        - player_pos: logical tile coordinates to draw the player dot.
        - is_room: optional predicate; if provided, only draw explored tiles that are rooms.
        """
        if not self.enabled:
            return

        if self.layout is None:
            logger.debug("Minimap draw skipped: no layout computed yet")
            return

        try:
            import arcade
        except Exception as exc:  # pragma: no cover - runtime import guard
            logger.error("Arcade import failed in MinimapRenderer.draw: %s", exc)
            return

        # Draw background panel
        l = self.layout
        arcade.draw_lrtb_rectangle_filled(
            l.origin_left,
            l.origin_left + l.pixel_width,
            l.origin_bottom + l.pixel_height,
            l.origin_bottom,
            MM_CONFIG.background_color,
        )
        # Border
        arcade.draw_lrtb_rectangle_outline(
            l.origin_left,
            l.origin_left + l.pixel_width,
            l.origin_bottom + l.pixel_height,
            l.origin_bottom,
            MM_CONFIG.border_color,
            border_width=1,
        )

        # Draw explored tiles
        ts = l.tile_size
        for (x, y) in self.model.explored():
            if is_room is not None and not is_room(x, y):
                continue
            left = l.origin_left + x * ts
            bottom = l.origin_bottom + y * ts
            arcade.draw_lrtb_rectangle_filled(
                left,
                left + ts,
                bottom + ts,
                bottom,
                MM_CONFIG.explored_color,
            )

        # Draw player position as a bright dot, if provided
        if player_pos is not None:
            px, py = player_pos
            if 0 <= px < self.model.width and 0 <= py < self.model.height:
                cx = l.origin_left + px * ts + ts / 2
                cy = l.origin_bottom + py * ts + ts / 2
                r = max(1, ts // 3)
                arcade.draw_circle_filled(cx, cy, r, MM_CONFIG.player_color)
