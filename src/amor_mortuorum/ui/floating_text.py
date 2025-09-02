from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol, Sequence, Tuple

logger = logging.getLogger(__name__)

Color = Tuple[int, int, int, int]  # RGBA 0-255
Point = Tuple[float, float]


class TextRenderer(Protocol):
    """Protocol for drawing text. Allows decoupling from Arcade in tests.

    Any renderer must implement draw_text with basic parameters.
    """

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        color: Color,
        font_size: int = 12,
        bold: bool = False,
        anchor_x: str = "center",
    ) -> None:
        ...


try:  # Optional Arcade adapter
    import arcade  # type: ignore

    class ArcadeTextRenderer:
        def draw_text(
            self,
            text: str,
            x: float,
            y: float,
            color: Color,
            font_size: int = 12,
            bold: bool = False,
            anchor_x: str = "center",
        ) -> None:  # pragma: no cover - optional adapter
            arcade.draw_text(
                text,
                x,
                y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
            )

except Exception:  # pragma: no cover - no arcade
    ArcadeTextRenderer = None  # type: ignore


@dataclass
class FloatingCombatText:
    """Single floating text entity that animates over time.

    If anchor_id is set, the text will follow the anchor each update via an anchor lookup callable.
    Otherwise, it moves with its own velocity.
    """

    text: str
    color: Color
    duration: float = 1.2
    font_size: int = 14
    bold: bool = False
    # initial position or offset relative to anchor
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 32.0  # upward drift px/sec
    gravity: float = -24.0  # vy dampening per second
    fade_in_ratio: float = 0.2
    fade_out_ratio: float = 0.3
    anchor_id: Optional[str] = None

    # internal state
    elapsed: float = 0.0
    expired: bool = False

    def update(self, dt: float, anchor_lookup: Optional[Callable[[str], Point]] = None) -> None:
        if self.expired:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.expired = True
            return

        # Velocity integration (simple Euler)
        if self.gravity != 0:
            self.vy += self.gravity * dt
        self.y += self.vy * dt
        self.x += self.vx * dt

        # If anchored, position is relative to anchor base
        if self.anchor_id and anchor_lookup:
            base_x, base_y = anchor_lookup(self.anchor_id)
            # Position is base + our animated offsets
            self.render_x = base_x + self.x
            self.render_y = base_y + self.y
        else:
            # Free-floating
            self.render_x = self.x
            self.render_y = self.y

    def alpha(self) -> int:
        if self.duration <= 0:
            return 0
        t = self.elapsed / self.duration
        if t < self.fade_in_ratio:
            a = t / max(1e-6, self.fade_in_ratio)
        elif t > 1.0 - self.fade_out_ratio:
            tail = (1.0 - t) / max(1e-6, self.fade_out_ratio)
            a = max(0.0, min(1.0, tail))
        else:
            a = 1.0
        return int(255 * a)

    def draw(self, renderer: TextRenderer) -> None:
        if self.expired:
            return
        a = self.alpha()
        r, g, b, _ = self.color
        color = (r, g, b, a)
        x = getattr(self, "render_x", self.x)
        y = getattr(self, "render_y", self.y)
        renderer.draw_text(self.text, x, y, color=color, font_size=self.font_size, bold=self.bold)


class FloatingTextManager:
    """Manages a collection of floating combat texts; update and draw each frame."""

    def __init__(self, max_texts: int = 64) -> None:
        if max_texts <= 0:
            raise ValueError("max_texts must be positive")
        self.max_texts = max_texts
        self._texts: List[FloatingCombatText] = []

    def add_text(self, fct: FloatingCombatText) -> None:
        if len(self._texts) >= self.max_texts:
            # Drop oldest to make room
            self._texts.pop(0)
        self._texts.append(fct)

    def add_effect(
        self,
        *,
        anchor_id: Optional[str],
        text: str,
        kind: str = "info",
        base_position: Optional[Point] = None,
        vertical_offset: float = 24.0,
        crit: bool = False,
    ) -> FloatingCombatText:
        """Convenience for creating color-coded floating texts.

        Args:
            anchor_id: Entity id to follow; if None, uses a fixed position.
            text: Text to display.
            kind: One of {"damage", "heal", "miss", "buff", "debuff", "info"}.
            base_position: Fixed position when anchor_id is None.
            vertical_offset: Starting Y offset above the anchor baseline.
            crit: Emphasize via bold and font size.
        """
        color_map = {
            "damage": (235, 64, 52, 255),
            "heal": (64, 220, 120, 255),
            "miss": (160, 160, 160, 255),
            "buff": (72, 147, 235, 255),
            "debuff": (168, 98, 235, 255),
            "info": (255, 255, 255, 255),
        }
        color = color_map.get(kind, color_map["info"])
        font_size = 16 + (4 if crit else 0)
        bold = crit

        if anchor_id is not None:
            x, y = 0.0, vertical_offset
        else:
            x, y = (base_position or (0.0, 0.0))
            y += vertical_offset

        fct = FloatingCombatText(
            text=text,
            color=color,
            duration=1.0 if not crit else 1.3,
            font_size=font_size,
            bold=bold,
            x=x,
            y=y,
            vx=0.0,
            vy=36.0,
            gravity=-28.0,
            fade_in_ratio=0.15,
            fade_out_ratio=0.35,
            anchor_id=anchor_id,
        )
        self.add_text(fct)
        return fct

    def update(self, dt: float, anchor_lookup: Optional[Callable[[str], Point]] = None) -> None:
        for t in self._texts:
            t.update(dt, anchor_lookup)
        # Cull expired
        self._texts = [t for t in self._texts if not t.expired]

    def draw(self, renderer: TextRenderer) -> None:
        for t in self._texts:
            t.draw(renderer)

    def active_count(self) -> int:
        return len(self._texts)
