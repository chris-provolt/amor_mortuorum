"""Records screen: lifetime statistics and achievements for the active profile."""
from __future__ import annotations

from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..systems.stats import stat_rows
from ..ui.theme import fs

TEXT = (215, 215, 230)
DIM = (120, 120, 135)
GOLD = (255, 215, 120)


class RecordsScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self._title: arcade.Text | None = None
        self._stats: List[arcade.Text] = []
        self._ach: List[arcade.Text] = []
        self._footer: arcade.Text | None = None

    def on_enter(self):
        super().on_enter()
        meta = self.app.state.meta
        data = self.app.state.data
        profile = self.app.state.save_manager.profile_id
        self._title = arcade.Text(
            f"Records   ({profile})", 0, 0, color=arcade.color.GHOST_WHITE, font_size=fs(26),
            anchor_x="center", anchor_y="center",
        )
        self._stats = [
            arcade.Text("Statistics", 0, 0, color=TEXT, font_size=fs(16), anchor_y="top")
        ] + [
            arcade.Text(f"{label:<16} {value:>8,}", 0, 0, color=DIM, font_size=fs(13),
                        anchor_y="top", font_name="Consolas")
            for label, value in stat_rows(meta)
        ]
        have = len(meta.achievements)
        self._ach = [
            arcade.Text(
                f"Achievements  {have}/{len(data.achievements)}", 0, 0, color=TEXT,
                font_size=fs(16), anchor_y="top",
            )
        ]
        for ach in data.achievements:
            got = ach.id in meta.achievements
            mark = "[x]" if got else "[ ]"
            self._ach.append(
                arcade.Text(
                    f"{mark} {ach.name}: {ach.desc}", 0, 0, color=GOLD if got else DIM,
                    font_size=fs(12), anchor_y="top",
                )
            )
        self._footer = arcade.Text(
            "Esc to return", 0, 0, color=DIM, font_size=fs(12), anchor_x="center"
        )
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - fs(44))
        top = height - fs(90)
        for i, t in enumerate(self._stats):
            t.position = (width * 0.08, top - i * fs(22))
        for i, t in enumerate(self._ach):
            t.position = (width * 0.42, top - i * fs(22))
        if self._footer is not None:
            self._footer.position = (width / 2, fs(24))

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 210))
        for t in [self._title, *self._stats, *self._ach, self._footer]:
            if t is not None:
                t.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if "cancel" in actions or "confirm" in actions:
            self.manager.pop()
            return True
        return False
