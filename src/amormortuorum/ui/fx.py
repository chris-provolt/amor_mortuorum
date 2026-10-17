"""Ambient effects drawn each frame: dust motes, embers, fog and light pools.

Everything is a pure function of time and a seed, so the scenes stay free of
``random`` and a frame always looks the same for the same inputs.
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

import arcade

RGB = Tuple[int, int, int]


def jitter(i: int, k: int = 0) -> float:
    """A fixed pseudo-random value in [0, 1) for particle ``i`` of effect ``k``."""
    return (math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1.0


def flicker(t: float, seed: int = 0, depth: float = 0.06) -> float:
    """A torch's brightness factor around 1.0: two incommensurate wobbles plus a
    rare gutter, so it never settles into a visible loop."""
    a = math.sin(t * 13.1 + seed) * math.sin(t * 7.3 + seed * 0.7)
    gutter = max(0.0, math.sin(t * 1.9 + seed * 1.3) - 0.92) * 4
    return 1.0 + depth * a - depth * gutter


def draw_motes(
    cx: float, cy: float, t: float, *, count: int = 20, radius: float = 110.0,
    color: RGB = (255, 230, 170), seed: int = 0, size: float = 1.6, alpha: int = 150,
) -> None:
    """Dust drifting slowly through a pool of light around (cx, cy)."""
    for k in range(count):
        a0 = jitter(k, seed) * math.tau
        r = (0.25 + 0.75 * jitter(k, seed + 1)) * radius
        speed = 0.15 + 0.25 * jitter(k, seed + 2)
        ang = a0 + t * speed * 0.3
        x = cx + math.cos(ang) * r + math.sin(t * 0.7 + k) * 6
        y = cy + math.sin(ang) * r * 0.8 + math.sin(t * 0.5 + k * 1.7) * 8
        twinkle = 0.5 + 0.5 * math.sin(t * (1.5 + jitter(k, seed + 3)) + k)
        fade = 1 - r / radius
        a = int(alpha * fade * (0.4 + 0.6 * twinkle))
        if a > 0:
            arcade.draw_circle_filled(x, y, size, (*color, a))


def draw_embers(
    x: float, y: float, t: float, *, count: int = 6, rise: float = 50.0, spread: float = 10.0,
    seed: int = 0, size: float = 1.5,
) -> None:
    """Sparks lifting off a flame at (x, y), each on its own cycle."""
    for k in range(count):
        period = 1.2 + jitter(k, seed) * 1.4
        life = ((t + jitter(k, seed + 1) * period) % period) / period
        px = x + (jitter(k, seed + 2) - 0.5) * spread + math.sin(t * 3 + k) * 3 * life
        py = y + life * rise
        a = int(220 * (1 - life) ** 1.5)
        colour = (255, 200 - int(90 * life), 60, a)
        arcade.draw_circle_filled(px, py, size * (1 - 0.5 * life), colour)


def draw_light_pool(x: float, y: float, radius: float, color: RGB, alpha: int = 60) -> None:
    """A soft radial glow: a few layered translucent discs."""
    for i in range(4):
        r = radius * (1 - i * 0.22)
        a = int(alpha * (i + 1) / 10)  # the discs add up to about ``alpha`` at the core
        arcade.draw_circle_filled(x, y, r, (*color, a))


def draw_fog(
    left: float, bottom: float, width: float, height: float, t: float, *, bands: int = 5,
    color: RGB = (180, 190, 220), alpha: int = 26, seed: int = 0,
) -> None:
    """Low fog drifting across a strip: wide translucent ellipses sliding sideways."""
    for k in range(bands):
        w = width * (0.35 + 0.35 * jitter(k, seed))
        h = height * (0.25 + 0.3 * jitter(k, seed + 1))
        speed = 6 + 10 * jitter(k, seed + 2)
        x = left + ((jitter(k, seed + 3) * width + t * speed) % (width + w)) - w / 2
        y = bottom + height * (0.2 + 0.6 * jitter(k, seed + 4)) + math.sin(t * 0.4 + k) * 4
        arcade.draw_ellipse_filled(x, y, w, h, (*color, alpha))


def draw_flame(x: float, y: float, t: float, size: float, seed: int = 0) -> None:
    """A small flickering flame: three nested tongues that lean and breathe."""
    f = flicker(t, seed, 0.12)
    lean = math.sin(t * 5 + seed) * size * 0.15
    for colour, scale in (((230, 90, 30, 230), 1.0), ((255, 160, 50, 240), 0.7),
                          ((255, 240, 160, 255), 0.4)):
        h = size * scale * f
        w = size * 0.45 * scale
        arcade.draw_triangle_filled(x - w, y, x + w, y, x + lean * scale, y + h, colour)
    arcade.draw_ellipse_filled(x, y, size * 0.9, size * 0.3, (255, 200, 90, 200))


def light_pulse(t: float, seed: int, period: float = 1.0) -> float:
    """A slow sine between 0 and 1 for breathing glows."""
    return 0.5 + 0.5 * math.sin(t * math.tau / period + seed)


def tint(color: Sequence[int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])  # type: ignore[return-value]


__all__ = [
    "jitter",
    "flicker",
    "draw_motes",
    "draw_embers",
    "draw_light_pool",
    "draw_fog",
    "draw_flame",
    "light_pulse",
    "tint",
]
