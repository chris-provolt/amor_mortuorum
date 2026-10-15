from __future__ import annotations

import logging
from typing import Any, List, Optional, Type

from .base_scene import BaseScene

logger = logging.getLogger(__name__)


class SceneManager:
    """A stack-based scene manager.

    - push(scene): push a new scene on top; pauses the previous top, calls on_enter
    - pop(): remove top scene; calls on_exit, then on_resume on the new top
    - replace(scene): convenience to pop then push
    - pop_until(scene_type): pop scenes until the top is an instance of scene_type
    - update/draw: only the top scene is active

    The manager is arcade-free so it can be unit-tested with a dummy window.
    """

    def __init__(self, app: Any):
        self._stack: List[BaseScene] = []
        self.app = app

    def push(self, scene: BaseScene) -> None:
        previous = self.current
        if previous is not None:
            previous.on_pause()
        scene.manager = self
        self._stack.append(scene)
        logger.debug("Scene pushed: %s", type(scene).__name__)
        scene.on_enter()

    def pop(self) -> Optional[BaseScene]:
        if not self._stack:
            return None
        scene = self._stack.pop()
        logger.debug("Scene popped: %s", type(scene).__name__)
        try:
            scene.on_exit()
        finally:
            scene.manager = None
        if self.current is not None:
            self.current.on_resume()
        return scene

    def replace(self, scene: BaseScene) -> None:
        # Pop without resuming the scene underneath; the new scene takes over immediately.
        if self._stack:
            old = self._stack.pop()
            try:
                old.on_exit()
            finally:
                old.manager = None
        scene.manager = self
        self._stack.append(scene)
        logger.debug("Scene replaced with: %s", type(scene).__name__)
        scene.on_enter()

    def pop_until(self, scene_type: Type[BaseScene]) -> Optional[BaseScene]:
        """Pop scenes until the top is an instance of ``scene_type``.

        Returns the scene now on top, or ``None`` if no such scene was in the stack
        (in which case the stack is left empty).
        """
        while self._stack and not isinstance(self._stack[-1], scene_type):
            scene = self._stack.pop()
            try:
                scene.on_exit()
            finally:
                scene.manager = None
        if self.current is not None:
            self.current.on_resume()
        return self.current

    def clear(self) -> None:
        while self._stack:
            scene = self._stack.pop()
            try:
                scene.on_exit()
            finally:
                scene.manager = None

    @property
    def current(self) -> Optional[BaseScene]:
        return self._stack[-1] if self._stack else None

    def __len__(self) -> int:
        return len(self._stack)

    def update(self, delta_time: float):
        if self.current:
            self.current.update(delta_time)

    def draw(self):
        if self.current:
            self.current.draw()

    # Input delegation
    def key_actions(self, actions: list[str], pressed: bool) -> bool:
        if self.current:
            return bool(self.current.on_key_actions(actions, pressed))
        return False

    def key_event(self, kind: str, key: int, modifiers: int):
        if not self.current:
            return
        if kind == "press":
            self.current.on_key_press(key, modifiers)
        elif kind == "release":
            self.current.on_key_release(key, modifiers)

    def mouse_event(self, kind: str, x: float, y: float, button: int, modifiers: int):
        if not self.current:
            return
        if kind == "press":
            self.current.on_mouse_press(x, y, button, modifiers)
        elif kind == "release":
            self.current.on_mouse_release(x, y, button, modifiers)

    def mouse_motion(self, x: float, y: float, dx: float, dy: float):
        if self.current:
            self.current.on_mouse_motion(x, y, dx, dy)

    def resize(self, width: int, height: int):
        for scene in self._stack:
            scene.on_resize(width, height)
