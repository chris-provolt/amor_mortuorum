import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Union

try:
    import arcade
except Exception:  # pragma: no cover - allow import in non-GL environments
    arcade = None  # type: ignore

Number = Union[int, float]

logger = logging.getLogger(__name__)


@dataclass
class OverlayStyle:
    """Visual configuration for the debug overlay.

    Attributes:
        font_name: Preferred font family (use monospace for aligned columns).
        font_size: Font size in points.
        text_color: RGBA tuple for text color.
        background_color: RGBA tuple for background rectangle (with alpha for translucency).
        margin: Outer margin from window edges (pixels).
        padding: Inner padding inside the background box (pixels).
        line_height: Vertical spacing between lines. If None, defaults to font_size * 1.2.
        max_width: Hard cap for background width (None means auto from content).
        anchor: Corner where the overlay is anchored. One of: "top-left", "top-right",
                "bottom-left", "bottom-right".
    """

    font_name: str = "Courier New"
    font_size: int = 14
    text_color: tuple = (255, 255, 255, 255)
    background_color: tuple = (0, 0, 0, 180)
    margin: int = 8
    padding: int = 8
    line_height: Optional[int] = None
    max_width: Optional[int] = None
    anchor: str = "top-left"

    def resolved_line_height(self) -> int:
        return int(self.line_height or (self.font_size * 1.2))


@dataclass
class GameTelemetry:
    """Holds the data points displayed by the debug overlay.

    All fields are optional. Missing values are rendered as "-" in the overlay.
    """

    seed: Optional[Union[int, str]] = None
    floor: Optional[int] = None
    entity_counts: Dict[str, int] = field(default_factory=dict)
    extras: Dict[str, Union[str, Number]] = field(default_factory=dict)

    def update_entities(self, entities: Mapping[str, int] | Iterable[str]) -> None:
        """Update entity counts.

        Accepts either:
        - a mapping of category -> count, or
        - an iterable of category names (each increments its category by one)
        """
        if isinstance(entities, Mapping):
            self.entity_counts = {str(k): int(v) for k, v in entities.items()}
        else:
            counts: Dict[str, int] = {}
            for name in entities:
                counts[str(name)] = counts.get(str(name), 0) + 1
            self.entity_counts = counts

    def set_extra(self, key: str, value: Union[str, Number]) -> None:
        self.extras[str(key)] = value


class FPSCounter:
    """Simple rolling FPS estimator based on a time window of recent frames.

    Keeps recent frame delta times and computes FPS as N / sum(dt) over the window.
    By default uses the last 1.0 seconds of frame history for a stable reading.
    """

    def __init__(self, time_window: float = 1.0) -> None:
        self.time_window = float(time_window)
        self._dts: List[float] = []
        self._accum: float = 0.0
        self._fps: float = 0.0

    @property
    def fps(self) -> float:
        return self._fps

    def reset(self) -> None:
        self._dts.clear()
        self._accum = 0.0
        self._fps = 0.0

    def update(self, dt: float) -> float:
        if dt <= 0:
            return self._fps
        self._dts.append(dt)
        self._accum += dt
        while self._accum > self.time_window and self._dts:
            oldest = self._dts.pop(0)
            self._accum -= oldest
        total_time = max(1e-6, sum(self._dts))
        frames = len(self._dts)
        self._fps = frames / total_time
        return self._fps


class DebugOverlay:
    """Interactive debug overlay for in-game telemetry.

    Features:
    - Toggle with F3 key (call on_key_press from your window/scene)
    - Shows FPS, PRNG seed, floor, and entity category counts
    - Draws a translucent background for legibility

    Integration:
        overlay = DebugOverlay(enabled=False)

        # In your window/scene update loop:
        def on_update(self, dt):
            overlay.on_update(dt)

        # In your window/scene draw:
        def on_draw(self):
            ...  # draw game
            overlay.on_draw()

        # In your window/scene key handling:
        def on_key_press(self, key, modifiers):
            overlay.on_key_press(key, modifiers)

        # Update telemetry from your game state periodically
        overlay.telemetry.seed = world.seed
        overlay.telemetry.floor = world.depth
        overlay.telemetry.update_entities({
            "mobs": len(world.mobs),
            "items": len(world.items),
            "projectiles": len(world.projectiles),
        })
    """

    def __init__(
        self,
        telemetry: Optional[GameTelemetry] = None,
        *,
        enabled: bool = False,
        style: Optional[OverlayStyle] = None,
    ) -> None:
        self.telemetry: GameTelemetry = telemetry or GameTelemetry()
        self.enabled: bool = enabled
        self.style = style or OverlayStyle()
        self._fps = FPSCounter()
        self._cached_lines: List[str] = []
        self._cache_invalid: bool = True

    # ------------- Public API -------------
    def set_enabled(self, value: bool) -> None:
        self.enabled = bool(value)

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def on_key_press(self, key: int, modifiers: int) -> None:
        if arcade is None:
            return
        if key == arcade.key.F3:
            self.toggle()

    def on_update(self, dt: float) -> None:
        """Advance internal counters such as FPS. Safe to call even when disabled."""
        self._fps.update(dt)
        # Invalidate cached lines because FPS has changed per frame
        self._cache_invalid = True

    def on_draw(self) -> None:
        """Render the overlay if enabled.

        This is a no-op if there is no active Arcade window or overlay is disabled.
        """
        if not self.enabled:
            return
        if arcade is None:
            logger.debug("Arcade not available; skipping overlay draw")
            return

        window = arcade.get_window()
        if window is None:
            logger.debug("No active window; skipping overlay draw")
            return

        lines = self.compose_lines()
        if not lines:
            return

        # Calculate layout
        style = self.style
        line_height = style.resolved_line_height()
        max_chars = max((len(line) for line in lines), default=0)
        char_px = max(6, int(style.font_size * 0.6))  # rough monospace estimate
        content_width = max_chars * char_px
        if style.max_width is not None:
            content_width = min(content_width, style.max_width)
        box_width = content_width + style.padding * 2
        box_height = len(lines) * line_height + style.padding * 2

        # Determine anchored box rectangle
        margin = style.margin
        left: float
        right: float
        top: float
        bottom: float
        if style.anchor == "top-left":
            left = margin
            right = left + box_width
            top = window.height - margin
            bottom = top - box_height
        elif style.anchor == "top-right":
            right = window.width - margin
            left = right - box_width
            top = window.height - margin
            bottom = top - box_height
        elif style.anchor == "bottom-left":
            left = margin
            right = left + box_width
            bottom = margin
            top = bottom + box_height
        elif style.anchor == "bottom-right":
            right = window.width - margin
            left = right - box_width
            bottom = margin
            top = bottom + box_height
        else:
            logger.warning("Unknown overlay anchor '%s', using top-left", style.anchor)
            left = margin
            right = left + box_width
            top = window.height - margin
            bottom = top - box_height

        # Background
        arcade.draw_lrtb_rectangle_filled(left, right, top, bottom, style.background_color)

        # Text lines
        x = left + style.padding
        y = top - style.padding - line_height
        for line in lines:
            try:
                text = arcade.Text(
                    line,
                    x=x,
                    y=y,
                    color=style.text_color,
                    font_name=style.font_name,
                    font_size=style.font_size,
                    anchor_x="left",
                    anchor_y="bottom",
                )
                text.draw()
            except Exception as e:  # pragma: no cover - draw safety
                logger.exception("Failed to draw overlay text: %s", e)
            y -= line_height

    # ------------- Composition -------------
    def compose_lines(self) -> List[str]:
        """Create the textual lines to render. Safe for testing without a window."""
        if not self._cache_invalid:
            return list(self._cached_lines)

        t = self.telemetry
        fps_val = self._fps.fps
        try:
            # Prefer arcade's internal FPS if available; fallback to computed
            if arcade is not None:
                win = arcade.get_window()
                if win is not None and hasattr(arcade, "get_fps"):
                    fps_val = float(arcade.get_fps())  # type: ignore[attr-defined]
        except Exception:
            pass

        lines: List[str] = []
        lines.append(f"FPS: {fps_val:5.1f}")
        seed_str = "-" if t.seed in (None, "", []) else str(t.seed)
        floor_str = "-" if t.floor in (None,) else str(t.floor)
        lines.append(f"Seed:  {seed_str}")
        lines.append(f"Floor: {floor_str}")

        if t.entity_counts:
            total = sum(max(0, int(v)) for v in t.entity_counts.values())
            parts = [f"{k}={int(v)}" for k, v in sorted(t.entity_counts.items())]
            ent_line = f"Entities: total={total} ({', '.join(parts)})"
        else:
            ent_line = "Entities: -"
        lines.append(ent_line)

        if t.extras:
            for k, v in sorted(t.extras.items()):
                lines.append(f"{k}: {v}")

        self._cached_lines = lines
        self._cache_invalid = False
        return list(lines)

    # ------------- Utility -------------
    def invalidate(self) -> None:
        self._cache_invalid = True


__all__ = [
    "DebugOverlay",
    "GameTelemetry",
    "OverlayStyle",
    "FPSCounter",
]
