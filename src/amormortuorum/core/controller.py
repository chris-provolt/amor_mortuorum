"""Game controller support (pyglet 2.1 Controller API) mapped onto input actions.

The mapping functions are pure so they can be unit-tested; ``ControllerInput``
attaches them to pyglet's hot-plug ``ControllerManager`` and feeds the
resulting actions into the scene stack exactly like key presses.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

STICK_THRESHOLD = 0.5

# Xbox-style button names as pyglet reports them.
BUTTON_ACTIONS: Dict[str, str] = {
    "a": "confirm",
    "b": "cancel",
    "x": "map",
    "y": "menu",
    "start": "pause",
    "back": "map",
    "guide": "pause",
}


def button_to_actions(button: str) -> List[str]:
    action = BUTTON_ACTIONS.get(button.lower())
    return [action] if action else []


def _direction_set(x: float, y: float, threshold: float) -> Tuple[str, ...]:
    out: List[str] = []
    if x <= -threshold:
        out.append("move_left")
    elif x >= threshold:
        out.append("move_right")
    if y <= -threshold:
        out.append("move_down")
    elif y >= threshold:
        out.append("move_up")
    return tuple(out)


def direction_edges(
    previous: Tuple[str, ...], x: float, y: float, threshold: float = STICK_THRESHOLD
) -> Tuple[Tuple[str, ...], List[str]]:
    """Turn a stick/dpad vector into newly pressed move actions.

    Returns ``(current_directions, newly_pressed)`` so holding a direction fires
    once, like a key press, until it is released and pushed again.
    """
    current = _direction_set(x, y, threshold)
    pressed = [d for d in current if d not in previous]
    return current, pressed


class ControllerInput:
    """Bridges every connected controller to ``dispatch(actions)``."""

    def __init__(self, dispatch: Callable[[List[str]], None]) -> None:
        self.dispatch = dispatch
        self._dpad: Tuple[str, ...] = ()
        self._stick: Tuple[str, ...] = ()
        self.manager = None
        self.controllers: list = []

    def start(self) -> bool:
        """Open every controller present and listen for hot-plug events."""
        try:
            from pyglet.input import ControllerManager
        except Exception as e:  # pragma: no cover - platform specific
            logger.info("Controllers unavailable: %s", e)
            return False
        try:
            self.manager = ControllerManager()
            self.manager.on_connect = self._on_connect
            self.manager.on_disconnect = self._on_disconnect
            for controller in self.manager.get_controllers():
                self._on_connect(controller)
        except Exception as e:  # pragma: no cover - platform specific
            logger.info("Controller discovery failed: %s", e)
            self.manager = None
            return False
        return True

    # Hot-plug

    def _on_connect(self, controller) -> None:
        try:
            controller.open()
        except Exception as e:  # pragma: no cover
            logger.info("Could not open controller %s: %s", getattr(controller, "name", "?"), e)
            return
        controller.on_button_press = self._on_button_press
        controller.on_dpad_motion = self._on_dpad_motion
        controller.on_stick_motion = self._on_stick_motion
        self.controllers.append(controller)
        logger.info("Controller connected: %s", getattr(controller, "name", "controller"))

    def _on_disconnect(self, controller) -> None:
        if controller in self.controllers:
            self.controllers.remove(controller)
        logger.info("Controller disconnected")

    # Events (pyglet 2.1 signatures)

    def _on_button_press(self, controller, button: str) -> None:
        actions = button_to_actions(button)
        if actions:
            self.dispatch(actions)

    def _on_dpad_motion(self, controller, vector) -> None:
        self._dpad, pressed = direction_edges(self._dpad, vector.x, vector.y)
        if pressed:
            self.dispatch(pressed)

    def _on_stick_motion(self, controller, stick: str, vector) -> None:
        if stick != "leftstick":
            return
        self._stick, pressed = direction_edges(self._stick, vector.x, vector.y)
        if pressed:
            self.dispatch(pressed)

    @property
    def connected(self) -> Optional[str]:
        if not self.controllers:
            return None
        return getattr(self.controllers[0], "name", "controller")


__all__ = ["BUTTON_ACTIONS", "button_to_actions", "direction_edges", "ControllerInput"]
