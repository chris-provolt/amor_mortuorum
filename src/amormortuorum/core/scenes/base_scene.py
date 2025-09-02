from __future__ import annotations

import logging
from typing import Optional

import arcade

logger = logging.getLogger(__name__)


class BaseScene:
    """
    Base class for all scenes in the game.

    Lifecycle hooks:
    - on_enter(): Called when scene is pushed onto the manager
    - on_exit(): Called when scene is popped from the manager
    - update(delta_time)
    - draw()

    Input hooks:
    - on_key_actions(actions: list[str], pressed: bool) -> bool
      Return True if the scene handled the action(s) to stop propagation
    - on_key_press(key, modifiers); on_key_release(key, modifiers)
    - on_mouse_press/release/motion
    """

    def __init__(self, app: arcade.Window) -> None:
        self.app = app
        self.manager: Optional["SceneManager"] = None  # set by SceneManager

    # Lifecycle
    def on_enter(self):
        logger.debug("%s.on_enter", type(self).__name__)

    def on_exit(self):
        logger.debug("%s.on_exit", type(self).__name__)

    def update(self, delta_time: float):
        pass

    def draw(self):
        pass

    # Input handling (override as needed)
    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        return False

    def on_key_press(self, key: int, modifiers: int):
        pass

    def on_key_release(self, key: int, modifiers: int):
        pass

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        pass

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        pass

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        pass


# Late import to avoid circular type reference for type hints
from .manager import SceneManager  # noqa: E402
