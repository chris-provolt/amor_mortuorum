from __future__ import annotations

import logging
from typing import List, Optional

import arcade

from .base_scene import BaseScene

logger = logging.getLogger(__name__)


class SceneManager:
    """A stack-based scene manager.

    - push(scene): push a new scene on top; calls on_enter
    - pop(): remove top scene; calls on_exit
    - replace(scene): convenience to pop then push
    - update/draw: only top scene is active for now

    Future: Could support overlay/UI scenes that draw underneath.
    """

    def __init__(self, app: arcade.Window):
        self._stack: List[BaseScene] = []
        self.app = app

    def push(self, scene: BaseScene) -> None:
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
        return scene

    def replace(self, scene: BaseScene) -> None:
        self.pop()
        self.push(scene)

    @property
    def current(self) -> Optional[BaseScene]:
        return self._stack[-1] if self._stack else None

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
        arcade.set_viewport(0, width, 0, height)
        # Scenes can override draw using current viewport; if needed, provide hook later
