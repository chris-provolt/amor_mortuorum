"""Bevelled window frames and gauges in the 16-bit RPG style.

A window is a vertical gradient (deep blue at the top fading darker towards
the bottom) with a bright double border and a dark outer line, the look of
classic console RPG menus. Gauges share the bevel so HP and MP bars sit
naturally inside them. Everything is drawn with Arcade's shape primitives
each frame; nothing here holds state.
"""
from __future__ import annotations

from typing import Tuple

import arcade

RGB = Tuple[int, int, int]

WINDOW_TOP: RGB = (34, 40, 104)
WINDOW_BOTTOM: RGB = (10, 12, 44)
BORDER_LIGHT: RGB = (226, 230, 244)
BORDER_MID: RGB = (132, 140, 196)
BORDER_DARK: RGB = (8, 8, 20)
GAUGE_BACK: RGB = (22, 18, 36)
GAUGE_RIM: RGB = (92, 92, 120)
BANDS = 10  # gradient steps per window


def draw_window(
    left: float, bottom: float, width: float, height: float, *, alpha: int = 235,
    top: RGB = WINDOW_TOP, bottom_color: RGB = WINDOW_BOTTOM,
) -> None:
    """A framed menu window with a vertical gradient fill."""
    band_h = height / BANDS
    for i in range(BANDS):
        t = i / max(1, BANDS - 1)  # 0 at the top band
        color = tuple(int(a * (1 - t) + b * t) for a, b in zip(top, bottom_color))
        y = bottom + height - (i + 1) * band_h
        arcade.draw_lbwh_rectangle_filled(left, y, width, band_h + 0.5, (*color, alpha))
    # Outer dark line, bright double border, inner mid line
    arcade.draw_lbwh_rectangle_outline(left, bottom, width, height, (*BORDER_DARK, alpha), 1)
    arcade.draw_lbwh_rectangle_outline(
        left + 1, bottom + 1, width - 2, height - 2, (*BORDER_LIGHT, alpha), 2
    )
    arcade.draw_lbwh_rectangle_outline(
        left + 3, bottom + 3, width - 6, height - 6, (*BORDER_MID, alpha), 1
    )


def draw_gauge(
    left: float, bottom: float, width: float, height: float, frac: float, color: RGB,
    *, back: RGB = GAUGE_BACK,
) -> None:
    """A bevelled bar filled to ``frac`` (0..1) with a lighter top edge."""
    frac = max(0.0, min(1.0, frac))
    arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, back)
    if frac > 0:
        fill_w = max(1.0, width * frac)
        arcade.draw_lbwh_rectangle_filled(left, bottom, fill_w, height, color)
        light = tuple(min(255, int(c * 1.35) + 20) for c in color)
        arcade.draw_lbwh_rectangle_filled(left, bottom + height - 2, fill_w, 2, light)
        dark = tuple(int(c * 0.6) for c in color)
        arcade.draw_lbwh_rectangle_filled(left, bottom, fill_w, 1, dark)
    arcade.draw_lbwh_rectangle_outline(left, bottom, width, height, GAUGE_RIM, 1)


def draw_cursor(x: float, y: float, size: float = 10, color: RGB = (255, 232, 140)) -> None:
    """A right-pointing selection cursor with a dark shadow."""
    shadow = [(x + 1, y - size / 2 - 1), (x + size + 1, y - 1), (x + 1, y + size / 2 - 1)]
    arcade.draw_polygon_filled(shadow, (10, 10, 20))
    arcade.draw_polygon_filled([(x, y - size / 2), (x + size, y), (x, y + size / 2)], color)


__all__ = [
    "WINDOW_TOP",
    "WINDOW_BOTTOM",
    "BORDER_LIGHT",
    "draw_window",
    "draw_gauge",
    "draw_cursor",
]
