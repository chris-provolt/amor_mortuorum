from __future__ import annotations

import logging
from typing import Tuple

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover - optional for test envs
    arcade = None

from ..engine.game_state import GameState
from ..engine.events import GameEvent
from ..dungeon.tiles import TileType

logger = logging.getLogger(__name__)

TILE_SIZE = 32
MARGIN = 2


class DungeonWindow:
    """Minimal Arcade window to visualize map, move player, and descend stairs.

    Note: This class is only created if Arcade is available. Tests focus on the
    logic layer, not rendering.
    """

    def __init__(self, state: GameState):
        if arcade is None:
            raise RuntimeError("Arcade package is not installed; cannot create window")
        self.state = state
        width = state.map_width * TILE_SIZE
        height = state.map_height * TILE_SIZE
        self._window = arcade.Window(width, height, title=f"Amor Mortuorum - B{state.floor}")
        self._window.on_draw = self.on_draw
        self._window.on_key_press = self.on_key_press
        state.add_listener(self._on_event)
        logger.info("Arcade window initialized (%dx%d)", width, height)

    def _on_event(self, event: GameEvent, state: GameState):
        if event is GameEvent.FLOOR_CHANGED:
            self._window.set_caption(f"Amor Mortuorum - B{state.floor}")
        self._window.invalidate()

    def run(self):
        arcade.run()

    def on_draw(self):
        arcade.start_render()
        # Draw tiles
        for y in range(self.state.map.height):
            for x in range(self.state.map.width):
                tile = self.state.map.get(x, y)
                color = tile.color
                cx = x * TILE_SIZE + TILE_SIZE // 2
                cy = (self.state.map.height - 1 - y) * TILE_SIZE + TILE_SIZE // 2
                arcade.draw_rectangle_filled(cx, cy, TILE_SIZE - MARGIN, TILE_SIZE - MARGIN, color)
        # Draw player
        px, py = self.state.player_pos
        cx = px * TILE_SIZE + TILE_SIZE // 2
        cy = (self.state.map.height - 1 - py) * TILE_SIZE + TILE_SIZE // 2
        arcade.draw_rectangle_filled(cx, cy, TILE_SIZE - MARGIN, TILE_SIZE - MARGIN, (60, 180, 255))

    def on_key_press(self, symbol, modifiers):
        if symbol in (arcade.key.LEFT, arcade.key.A):
            self.state.move(-1, 0)
        elif symbol in (arcade.key.RIGHT, arcade.key.D):
            self.state.move(1, 0)
        elif symbol in (arcade.key.UP, arcade.key.W):
            self.state.move(0, -1)
        elif symbol in (arcade.key.DOWN, arcade.key.S):
            self.state.move(0, 1)


def run(seed: int | None = None, width: int = 32, height: int = 18):  # pragma: no cover - manual usage
    """Launch a simple interactive window for manual testing."""
    if arcade is None:
        raise RuntimeError("Arcade is not installed. Please install 'arcade' to run the app.")
    logging.basicConfig(level=logging.INFO)
    state = GameState(seed=seed, map_width=width, map_height=height)
    win = DungeonWindow(state)
    win.run()
