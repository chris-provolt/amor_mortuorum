"""Very small stub of the ``arcade`` API used by unit tests."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, Tuple


class Window:
    """Simplified stand-in for :class:`arcade.Window`."""

    def __init__(self, width: int = 800, height: int = 600, title: str = "", **_: Dict) -> None:
        self.width = width
        self.height = height
        self.title = title

    def run(self) -> None:  # pragma: no cover - behaviourless stub
        """No-op stub matching the real API."""
        pass


color = SimpleNamespace(
    BLACK=(0, 0, 0),
    GRAY=(128, 128, 128),
    GHOST_WHITE=(248, 248, 255),
)


class _KeyModule:
    _codes: Dict[str, int] = {
        "UP": 1,
        "DOWN": 2,
        "LEFT": 3,
        "RIGHT": 4,
        "ENTER": 5,
        "SPACE": 6,
        "ESCAPE": 7,
        "BACKSPACE": 8,
        "TAB": 9,
        "P": 10,
        "F3": 11,
    }

    def __getattr__(self, name: str) -> int:
        if name in self._codes:
            return self._codes[name]
        if len(name) == 1 and name.isalpha():
            code = ord(name.upper())
            self._codes[name] = code
            return code
        raise AttributeError(name)


key = _KeyModule()


def draw_text(*_: Tuple) -> None:  # pragma: no cover - no-op stub
    pass


def start_render() -> None:  # pragma: no cover - no-op stub
    pass


def set_background_color(*_: Tuple) -> None:  # pragma: no cover - no-op stub
    pass


def set_viewport(*_: Tuple) -> None:  # pragma: no cover - no-op stub
    pass


def close_window() -> None:  # pragma: no cover - no-op stub
    pass


def run() -> None:  # pragma: no cover - no-op stub
    pass
