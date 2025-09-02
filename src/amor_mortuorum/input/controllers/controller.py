from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..actions import InputAction, InputEvent
from ..mapping import InputMapper

logger = logging.getLogger(__name__)


class GameController:
    """Stubbed game controller interface for future controller support.

    This class currently provides a no-op implementation that compiles and runs
    without external dependencies. It models a minimal API that higher layers
    can rely on. Future work can implement actual controller discovery and
    event translation (e.g., via Arcade/Pyglet or SDL).

    Usage:
        controller = GameController()
        controller.connect()
        controller.update()
        events = controller.get_events()
    """

    def __init__(self, mapper: Optional[InputMapper] = None) -> None:
        self.mapper = mapper or InputMapper.default()
        self._connected: bool = False
        self._event_queue: List[InputEvent] = []
        # Default button name to action mapping for future controllers
        # These are logical button labels; actual backend should alias to these.
        self._button_bindings: Dict[str, InputAction] = {
            "DPAD_UP": InputAction.MOVE_UP,
            "DPAD_DOWN": InputAction.MOVE_DOWN,
            "DPAD_LEFT": InputAction.MOVE_LEFT,
            "DPAD_RIGHT": InputAction.MOVE_RIGHT,
            "START": InputAction.CONFIRM,
            "A": InputAction.CONFIRM,
            "B": InputAction.BACK,
            "BACK": InputAction.BACK,
        }

    # ---------- Lifecycle ----------
    def connect(self) -> bool:
        """Attempt to connect to a controller.

        Currently a stub that marks the controller as available. Returns True to
        indicate that the interface is usable, even if no physical controller is
        connected. Future implementations may return False on failure.
        """
        self._connected = True
        logger.debug("GameController connected (stub)")
        return self._connected

    @property
    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False
        logger.debug("GameController disconnected (stub)")

    # ---------- Event handling ----------
    def queue_button_event(self, button_name: str, pressed: bool) -> None:
        """Queue a synthetic controller event (useful for tests/simulations)."""
        action = self._button_bindings.get(button_name.upper())
        if action is None:
            return
        self._event_queue.append(InputEvent(action=action, pressed=pressed, source="controller"))

    def update(self) -> None:
        """Poll the controller state and queue InputEvents.

        Stub: No-op for now. Future implementations will read hardware state and
        push events into _event_queue.
        """
        # No hardware polling in stub implementation.
        pass

    def get_events(self) -> List[InputEvent]:
        events = list(self._event_queue)
        self._event_queue.clear()
        return events


__all__ = ["GameController"]
