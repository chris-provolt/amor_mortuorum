from __future__ import annotations

import logging

import arcade

from ..core.scenes.base_scene import BaseScene

logger = logging.getLogger(__name__)


class MainMenuScene(BaseScene):
    """Placeholder main menu scene.

    Press Enter/Space (confirm) to proceed; Esc to exit.
    """

    def __init__(self, app):
        super().__init__(app)
        self._title: arcade.Text | None = None
        self._hint: arcade.Text | None = None

    def on_enter(self):
        super().on_enter()
        self._title = arcade.Text(
            "Amor Mortuorum",
            0,
            0,
            color=arcade.color.GHOST_WHITE,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
        )
        self._hint = arcade.Text(
            "Press Enter to Start - Esc to Quit",
            0,
            0,
            color=arcade.color.GRAY,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height / 2 + 80)
        if self._hint is not None:
            self._hint.position = (width / 2, height / 2)

    def draw(self):
        if self._title is not None:
            self._title.draw()
        if self._hint is not None:
            self._hint.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if "confirm" in actions:
            logger.info("Start selected (placeholder)")
            # Replaced by the real menu once the Graveyard scene exists
            return True
        if "cancel" in actions:
            logger.info("Exit selected from MainMenu")
            self.app.close()
            return True
        return False
