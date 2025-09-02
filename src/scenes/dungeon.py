from __future__ import annotations

import logging
try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover - tests may stub arcade
    arcade = None  # type: ignore

logger = logging.getLogger(__name__)


class DungeonView(getattr(__import__(__name__), 'arcade', type('A', (), {'View': object})).View):
    """Placeholder Dungeon scene.

    This minimal implementation exists to satisfy transitions from the Graveyard.
    It can be replaced/extended by the full Dungeon implementation.
    """

    def __init__(self, start_floor: int = 1) -> None:
        # Avoid calling super().__init__ if arcade is stubbed/missing
        try:
            super().__init__()
        except Exception:
            pass
        self.start_floor = start_floor

    def on_show_view(self) -> None:  # pragma: no cover - visual
        if arcade:
            arcade.set_background_color((0, 0, 0))
        logger.info("Entered Dungeon at floor %s", self.start_floor)

    def on_draw(self) -> None:  # pragma: no cover - visual
        if not arcade:
            return
        arcade.start_render()
        arcade.draw_text(
            f"Dungeon - Floor {self.start_floor}",
            20,
            20,
            (200, 200, 200),
            18,
        )
