"""Heads-up display: party vitals, floor, gold, seed, and a short message log."""
from __future__ import annotations

from collections import deque
from typing import Deque, Optional

import arcade

from ..systems.run import Run
from . import frame
from .theme import fs

TEXT = (230, 230, 240)
DIM = (150, 150, 165)


class Hud:
    def __init__(self, app, max_messages: int = 3) -> None:
        self.app = app
        self._status = arcade.Text("", 12, 0, color=TEXT, font_size=fs(14), anchor_y="top")
        self._lines = [
            arcade.Text("", 12, 0, color=DIM, font_size=fs(12), anchor_y="top")
            for _ in range(max_messages)
        ]
        self.messages: Deque[str] = deque(maxlen=max_messages)
        self.on_resize(app.width, app.height)

    def on_resize(self, width: int, height: int) -> None:
        self._status.position = (12, height - 10)
        for i, line in enumerate(self._lines):
            line.position = (12, height - fs(34) - i * fs(17))

    def push(self, text: str) -> None:
        self.messages.append(text)

    def clear(self) -> None:
        self.messages.clear()

    def draw(self, run: Optional[Run], extra: str = "") -> None:
        height = self.app.height
        panel_h = fs(92)
        frame.draw_window(-4, height - panel_h, self.app.width + 8, panel_h + 8, alpha=215)
        if run is not None:
            p = run.leader
            members = "   ".join(
                f"{m.name} {max(0, m.hp)}/{m.max_hp}" + ("" if m.is_alive else " (down)")
                for m in run.party
            )
            status = (
                f"{members}   Lv {p.level}   Gold {p.gold}   Floor B{run.floor}   Seed {run.seed}"
            )
        else:
            status = "Amor Mortuorum"
        if extra:
            status += f"   {extra}"
        if self._status.text != status:
            self._status.text = status
        self._status.draw()
        for line, text in zip(self._lines, list(self.messages)[::-1]):
            if line.text != text:
                line.text = text
            line.draw()
