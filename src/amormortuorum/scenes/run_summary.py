"""End-of-run (or resurrection) summary screen."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..systems.run import RunSummary

logger = logging.getLogger(__name__)


class RunSummaryScene(BaseScene):
    def __init__(self, app, summary: RunSummary, message: str):
        super().__init__(app)
        self.summary = summary
        self.message = message
        self._lines: List[arcade.Text] = []

    def on_enter(self):
        super().on_enter()
        s = self.summary
        title = "You wake among the graves" if s.revived else "Your descent ends"
        body = [
            self.message,
            "",
            f"Floor reached: B{s.floor_reached}",
            f"Gold carried: {s.gold}",
            f"Cause: {s.cause}",
            "",
            "Press Enter to continue",
        ]
        self._lines = [
            arcade.Text(
                title, 0, 0, color=arcade.color.GHOST_WHITE, font_size=30,
                anchor_x="center", anchor_y="center",
            )
        ] + [
            arcade.Text(
                line, 0, 0, color=(200, 200, 215), font_size=16,
                anchor_x="center", anchor_y="center",
            )
            for line in body
        ]
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        for i, text in enumerate(self._lines):
            text.position = (width / 2, height * 0.68 - i * 34)

    def draw(self):
        for text in self._lines:
            text.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed or "confirm" not in actions:
            return False
        if self.summary.revived:
            from .graveyard import GraveyardScene

            self.manager.replace(GraveyardScene(self.app))
        else:
            self.app.state.run = None
            self.manager.pop()
        return True
