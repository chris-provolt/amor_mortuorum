from __future__ import annotations

import logging
from typing import Dict, Any

from amormortuorum.state.player import PlayerStats
from amormortuorum.state.session import GameSession

logger = logging.getLogger(__name__)

# Arcade is optional for testing environments; we guard imports.
try:
    import arcade
except Exception:  # pragma: no cover - not relevant in headless tests
    arcade = None  # type: ignore


class HUD:
    """
    Heads-Up Display for core run-time stats:
    - HP / MP bars and values
    - Floor number
    - Gold
    - Minimap visibility indicator (icon or text)

    The HUD listens to PlayerStats changes to update live and reads GameSession for
    floor/minimap state. draw() uses Arcade when available; otherwise, the state can
    be inspected via get_display_data() for logic tests.
    """

    def __init__(self, session: GameSession, player: PlayerStats):
        self.session = session
        self.player = player
        self._cache: Dict[str, Any] = {}
        self.player.add_listener(self._on_player_change)
        self._recalculate()

    # --- Event handlers ---
    def _on_player_change(self, event: str, payload: Dict[str, Any]) -> None:
        logger.debug("HUD received PlayerStats event: %s -> %s", event, payload)
        self._recalculate()

    def notify_session_changed(self) -> None:
        """Call when session values that HUD displays change (e.g., floor, minimap)."""
        self._recalculate()

    # --- Calculation & state snapshot ---
    def _recalculate(self) -> None:
        self._cache = {
            "hp": f"{self.player.hp}/{self.player.max_hp}",
            "mp": f"{self.player.mp}/{self.player.max_mp}",
            "gold": self.player.gold,
            "floor": self.session.floor,
            "minimap_visible": self.session.minimap_visible,
        }
        logger.debug("HUD recalculated: %s", self._cache)

    def get_display_data(self) -> Dict[str, Any]:
        """Return a snapshot of the HUD's user-facing data for testing/UI binding."""
        return dict(self._cache)

    # --- Rendering (optional, uses Arcade) ---
    def draw(self, window_width: int, window_height: int) -> None:  # pragma: no cover - visual
        if arcade is None:
            logger.debug("Arcade not available; HUD draw() is a no-op in this environment.")
            return

        padding = 12
        x = padding
        y = window_height - padding

        hp_text = f"HP: {self._cache['hp']}"
        mp_text = f"MP: {self._cache['mp']}"
        floor_text = f"B{self._cache['floor']:02d}"
        gold_text = f"Gold: {self._cache['gold']}"
        mini_text = "[M] Minimap: On" if self._cache["minimap_visible"] else "[M] Minimap: Off"

        # Draw background panel (semi-transparent)
        bg_height = 90
        arcade.draw_rectangle_filled(
            x + 220, window_height - bg_height / 2 - 8, 440, bg_height, color=(10, 10, 10, 160)
        )

        # Draw text lines
        arcade.draw_text(hp_text, x, y - 24, arcade.color.WHITE, 14)
        arcade.draw_text(mp_text, x, y - 46, arcade.color.WHITE, 14)
        arcade.draw_text(floor_text, x + 300, y - 24, arcade.color.ANTIQUE_WHITE, 16)
        arcade.draw_text(gold_text, x + 300, y - 46, arcade.color.GOLD, 14)
        arcade.draw_text(mini_text, x, y - 68, arcade.color.LIGHT_GRAY, 12)

        # Optional: simple bars
        self._draw_bar(x + 60, y - 18, 180, 8, self.player.hp, self.player.max_hp, (200, 50, 50))
        self._draw_bar(x + 60, y - 40, 180, 8, self.player.mp, self.player.max_mp, (50, 100, 200))

    def _draw_bar(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        value: int,
        max_value: int,
        color: tuple,
    ) -> None:  # pragma: no cover - visual helper
        if arcade is None or max_value <= 0:
            return
        pct = max(0.0, min(1.0, value / float(max_value)))
        arcade.draw_rectangle_filled(x, y, width, height, (60, 60, 60))
        arcade.draw_rectangle_filled(x - width / 2 + (width * pct) / 2, y, width * pct, height, color)
