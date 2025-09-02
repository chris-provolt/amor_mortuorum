from __future__ import annotations

import logging

import arcade

from ..core.scenes.base_scene import BaseScene
from .main_menu import MainMenuScene

logger = logging.getLogger(__name__)


class BootScene(BaseScene):
    """Simple splash/boot scene.

    Displays title briefly then transitions to main menu.
    """

    def __init__(self, app: arcade.Window):
        super().__init__(app)
        self._timer = 0.0
        self._min_time = 1.0  # seconds to show boot screen

    def update(self, delta_time: float):
        self._timer += delta_time
        if self._timer >= self._min_time:
            logger.info("Boot complete, transitioning to Main Menu")
            self.manager.replace(MainMenuScene(self.app))

    def draw(self):
        arcade.draw_text(
            "Amor Mortuorum",
            self.app.width / 2,
            self.app.height / 2,
            color=arcade.color.GHOST_WHITE,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Booting...",
            self.app.width / 2,
            self.app.height / 2 - 60,
            color=arcade.color.GRAY,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )
