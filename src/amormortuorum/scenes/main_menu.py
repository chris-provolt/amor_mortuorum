from __future__ import annotations

import logging

import arcade

from ..core.scenes.base_scene import BaseScene

logger = logging.getLogger(__name__)


class MainMenuScene(BaseScene):
    """Placeholder main menu scene.

    Press Enter/Space (confirm) to proceed; Esc to exit.
    """

    def draw(self):
        arcade.draw_text(
            "Amor Mortuorum",
            self.app.width / 2,
            self.app.height / 2 + 80,
            color=arcade.color.GHOST_WHITE,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Press Enter to Start • Esc to Quit",
            self.app.width / 2,
            self.app.height / 2,
            color=arcade.color.GRAY,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if "confirm" in actions:
            logger.info("Start selected (placeholder)")
            # Future: transition to game scene
            return True
        if "cancel" in actions:
            logger.info("Exit selected from MainMenu")
            arcade.close_window()
            return True
        return False
