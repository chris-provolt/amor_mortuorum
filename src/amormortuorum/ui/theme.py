"""UI scale shared by every screen (set from ``settings.video.ui_scale``)."""
from __future__ import annotations

_scale = 1.0
MIN_SCALE = 0.8
MAX_SCALE = 1.6


def set_ui_scale(value: float) -> float:
    """Clamp and store the global UI scale; returns the value in effect."""
    global _scale
    _scale = max(MIN_SCALE, min(MAX_SCALE, float(value)))
    return _scale


def ui_scale() -> float:
    return _scale


def fs(size: float) -> int:
    """Scale a design-time font size or spacing to the current UI scale."""
    return max(6, int(round(size * _scale)))


__all__ = ["set_ui_scale", "ui_scale", "fs", "MIN_SCALE", "MAX_SCALE"]
