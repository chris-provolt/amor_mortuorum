from __future__ import annotations

import logging
from typing import Optional

import arcade

from .core.input import InputManager
from .core.scenes.manager import SceneManager
from .core.settings import Settings
from .scenes.boot import BootScene

logger = logging.getLogger(__name__)


class GameApp(arcade.Window):
    """
    The main game window and application lifecycle manager.

    Responsibilities:
    - Configure and initialize the Arcade window using Settings
    - Own the SceneManager and InputManager
    - Delegate events (update/draw/input) to the active Scene
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Window configuration
        super().__init__(
            width=settings.video.width,
            height=settings.video.height,
            title="Amor Mortuorum",
            fullscreen=settings.video.fullscreen,
            resizable=True,
            vsync=settings.video.vsync,
            center_window=True,
        )

        # Apply scaling for UI/text (logical to physical)
        arcade.set_viewport(0, self.width, 0, self.height)

        # Background
        arcade.set_background_color(arcade.color.BLACK)

        # Managers
        self.scene_manager = SceneManager(self)
        self.input = InputManager(self, settings.input.mapping)

        # Boot into the first scene
        self.scene_manager.push(BootScene(self))

        logger.info(
            "GameApp initialized: %dx%d fullscreen=%s vsync=%s",
            settings.video.width,
            settings.video.height,
            settings.video.fullscreen,
            settings.video.vsync,
        )

    # Arcade lifecycle
    def on_draw(self):  # noqa: N802 (arcade API)
        arcade.start_render()
        self.scene_manager.draw()

    def on_update(self, delta_time: float):  # noqa: N802 (arcade API)
        self.scene_manager.update(delta_time)

    # Input events: delegate through InputManager, then to scene if not handled
    def on_key_press(self, key: int, modifiers: int):  # noqa: N802 (arcade API)
        actions = self.input.process_key_press(key, modifiers)
        # Let active scene consume the action(s)
        handled = self.scene_manager.key_actions(actions, pressed=True)
        if not handled:
            # If no action handled, pass raw event to scene
            self.scene_manager.key_event("press", key, modifiers)

    def on_key_release(self, key: int, modifiers: int):  # noqa: N802 (arcade API)
        actions = self.input.process_key_release(key, modifiers)
        handled = self.scene_manager.key_actions(actions, pressed=False)
        if not handled:
            self.scene_manager.key_event("release", key, modifiers)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):  # noqa: N802
        self.scene_manager.mouse_event("press", x, y, button, modifiers)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):  # noqa: N802
        self.scene_manager.mouse_event("release", x, y, button, modifiers)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):  # noqa: N802
        self.scene_manager.mouse_motion(x, y, dx, dy)

    def on_resize(self, width: int, height: int):  # noqa: N802 (arcade API)
        logger.debug("Window resized: %dx%d", width, height)
        super().on_resize(width, height)
        self.scene_manager.resize(width, height)

    def run(self) -> None:
        """Start the main loop."""
        logger.info("Starting main loop")
        arcade.run()

    # Integrations & helpers
    def set_fullscreen(self, fullscreen: Optional[bool] = None) -> None:
        if fullscreen is None:
            fullscreen = not self.fullscreen
        self.set_fullscreen(fullscreen)
        logger.info("Fullscreen toggled: %s", fullscreen)

