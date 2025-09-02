from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover
    arcade = None  # type: ignore

log = logging.getLogger(__name__)


@dataclass
class Button:
    x: float
    y: float
    width: float
    height: float
    text: str
    on_click: Callable[[], None]
    disabled: bool = False
    center: bool = True

    def draw(self) -> None:  # pragma: no cover - rendering
        if arcade is None:
            return
        color = arcade.color.DARK_BLUE if not self.disabled else arcade.color.GRAY
        arcade.draw_rectangle_filled(
            self.x, self.y, self.width, self.height, color
        )
        arcade.draw_rectangle_outline(
            self.x, self.y, self.width, self.height, arcade.color.WHITE, 2
        )
        if self.center:
            arcade.draw_text(
                self.text,
                self.x,
                self.y - 10,
                arcade.color.WHITE,
                16,
                width=self.width,
                align="center",
                anchor_x="center",
                anchor_y="center",
            )
        else:
            arcade.draw_text(self.text, self.x + 10, self.y - 8, arcade.color.WHITE, 16)

    def hit_test(self, x: float, y: float) -> bool:
        return (
            self.x - self.width / 2 <= x <= self.x + self.width / 2
            and self.y - self.height / 2 <= y <= self.y + self.height / 2
        )

    def click(self) -> None:
        if not self.disabled:
            try:
                self.on_click()
            except Exception:  # pragma: no cover - user code
                log.exception("Button click handler failed: %s", self.text)


@dataclass
class Toggle:
    x: float
    y: float
    text: str
    value: bool
    on_toggle: Callable[[bool], None]

    def draw(self) -> None:  # pragma: no cover - rendering
        if arcade is None:
            return
        label = f"{self.text}: {'ON' if self.value else 'OFF'}"
        arcade.draw_text(label, self.x, self.y, arcade.color.WHITE, 16)

    def hit_test(self, x: float, y: float) -> bool:
        # crude bbox for text; simplify handling
        return self.x <= x <= self.x + 300 and self.y - 20 <= y <= self.y + 10

    def click(self) -> None:
        self.value = not self.value
        try:
            self.on_toggle(self.value)
        except Exception:  # pragma: no cover
            log.exception("Toggle handler failed: %s", self.text)


@dataclass
class Slider:
    x: float
    y: float
    width: float
    text: str
    value: float  # 0..1
    on_change: Callable[[float], None]

    def draw(self) -> None:  # pragma: no cover - rendering
        if arcade is None:
            return
        # Bar
        arcade.draw_line(self.x, self.y, self.x + self.width, self.y, arcade.color.WHITE, 2)
        # Knob
        knob_x = self.x + self.value * self.width
        arcade.draw_circle_filled(knob_x, self.y, 8, arcade.color.LIGHT_GRAY)
        # Label
        arcade.draw_text(f"{self.text}: {int(self.value*100)}%", self.x, self.y + 10, arcade.color.WHITE, 14)

    def on_drag(self, x: float) -> None:
        rel = (x - self.x) / self.width
        rel = max(0.0, min(1.0, rel))
        self.value = rel
        try:
            self.on_change(self.value)
        except Exception:  # pragma: no cover
            log.exception("Slider handler failed: %s", self.text)

    def hit_test(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y - 10 <= y <= self.y + 10
