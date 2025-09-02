from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class InputAction(Enum):
    """Logical input actions used throughout the game.

    This enum abstracts away the details of the physical input devices
    (keyboard, gamepad, etc.) so that the game logic operates solely on
    semantic actions.
    """

    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    CONFIRM = auto()  # e.g., Enter/Start
    BACK = auto()  # e.g., Escape/Back/B


@dataclass(frozen=True)
class InputEvent:
    """Represents a press or release of a logical input action.

    Attributes:
        action: The logical action triggered.
        pressed: True if this is a key/button down event; False if up.
        source: Optional string describing the source device (e.g., "keyboard", "controller").
    """

    action: InputAction
    pressed: bool
    source: Optional[str] = None


__all__ = ["InputAction", "InputEvent"]
