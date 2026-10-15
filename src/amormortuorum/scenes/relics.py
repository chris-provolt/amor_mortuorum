"""Relics of the Veil collection screen."""
from __future__ import annotations

from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..systems.relics import collection_rows, describe_passive, passive_totals

TEXT = (215, 215, 230)
DIM = (120, 120, 135)
GOLD = (255, 215, 120)


class RelicsScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self._title: arcade.Text | None = None
        self._rows: List[List[arcade.Text]] = []
        self._footer: arcade.Text | None = None

    def on_enter(self):
        super().on_enter()
        meta = self.app.state.meta
        data = self.app.state.data
        rows = collection_rows(meta, data)
        have = sum(1 for _, got in rows if got)
        self._title = arcade.Text(
            f"Relics of the Veil   {have}/{len(rows)}", 0, 0, color=arcade.color.GHOST_WHITE,
            font_size=26, anchor_x="center", anchor_y="center",
        )
        self._rows = []
        for relic, got in rows:
            name = relic.name if got else "? ? ?"
            desc = relic.desc if got else "Not yet found."
            bonus = describe_passive(relic.passive) if got else ""
            name_color = GOLD if got else DIM
            desc_color = TEXT if got else DIM
            self._rows.append(
                [
                    arcade.Text(name, 0, 0, color=name_color, font_size=16, anchor_y="top"),
                    arcade.Text(desc, 0, 0, color=desc_color, font_size=12, anchor_y="top"),
                    arcade.Text(
                        bonus, 0, 0, color=TEXT, font_size=12, anchor_x="right", anchor_y="top"
                    ),
                ]
            )
        totals = describe_passive(passive_totals(meta, data)) or "none yet"
        self._footer = arcade.Text(
            f"Passives in effect: {totals}     Esc to return", 0, 0, color=TEXT, font_size=13,
            anchor_x="center",
        )
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - 44)
        left = width * 0.12
        right = width * 0.88
        top = height - 90
        step = max(44, (height - 150) / max(1, len(self._rows)))
        for i, (name, desc, bonus) in enumerate(self._rows):
            y = top - i * step
            name.position = (left, y)
            desc.position = (left + 16, y - 20)
            bonus.position = (right, y)
        if self._footer is not None:
            self._footer.position = (width / 2, 24)

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 210))
        if self._title is not None:
            self._title.draw()
        for row in self._rows:
            for text in row:
                if text.text:
                    text.draw()
        if self._footer is not None:
            self._footer.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if "cancel" in actions or "confirm" in actions:
            self.manager.pop()
            return True
        return False
