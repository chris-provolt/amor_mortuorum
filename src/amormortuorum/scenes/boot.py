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

    def __init__(self, app):
        super().__init__(app)
        self._timer = 0.0
        self._min_time = 1.0  # seconds to show boot screen
        self._title: arcade.Text | None = None
        self._subtitle: arcade.Text | None = None

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
        self._subtitle = arcade.Text(
            "Booting...",
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
            self._title.position = (width / 2, height / 2)
        if self._subtitle is not None:
            self._subtitle.position = (width / 2, height / 2 - 60)

    def update(self, delta_time: float):
        self._timer += delta_time
        if self._timer >= self._min_time:
            logger.info("Boot complete, transitioning to Main Menu")
            self.manager.replace(MainMenuScene(self.app))

    def draw(self):
        if self._title is not None:
            self._title.draw()
        if self._subtitle is not None:
            self._subtitle.draw()
