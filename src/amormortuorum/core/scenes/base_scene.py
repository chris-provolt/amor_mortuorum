from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from .manager import SceneManager

logger = logging.getLogger(__name__)


class BaseScene:
    """
    Base class for all scenes in the game.

    Lifecycle hooks:
    - on_enter(): Called when scene is pushed onto the manager
    - on_exit(): Called when scene is popped from the manager
    - on_pause(): Called when another scene is pushed on top of this one
    - on_resume(): Called when the scene above this one is popped
    - on_resize(width, height): Called when the window is resized
    - update(delta_time)
    - draw()

    Input hooks:
    - on_key_actions(actions: list[str], pressed: bool) -> bool
      Return True if the scene handled the action(s) to stop propagation
    - on_key_press(key, modifiers); on_key_release(key, modifiers)
    - on_mouse_press/release/motion

    ``app`` is the window (``GameApp``); scenes reach shared state via ``app.ctx``.
    It is typed as ``Any`` so the scene stack can be unit-tested with a dummy object.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self.manager: Optional["SceneManager"] = None  # set by SceneManager

    # Lifecycle
    def on_enter(self):
        logger.debug("%s.on_enter", type(self).__name__)

    def on_exit(self):
        logger.debug("%s.on_exit", type(self).__name__)

    def on_pause(self):
        logger.debug("%s.on_pause", type(self).__name__)

    def on_resume(self):
        logger.debug("%s.on_resume", type(self).__name__)

    def on_resize(self, width: int, height: int):
        pass

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
