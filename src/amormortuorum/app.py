from __future__ import annotations

import logging
from typing import Optional

import arcade

from .core.context import GameContext
from .core.input import InputManager
from .core.scenes.manager import SceneManager
from .core.settings import Settings
from .persistence import SaveError, SaveManager

logger = logging.getLogger(__name__)


class GameApp(arcade.Window):
    """
    The main game window and application lifecycle manager.

    Responsibilities:
    - Configure and initialize the Arcade window using Settings
    - Own the GameContext, SceneManager and InputManager
    - Delegate events (update/draw/input) to the active Scene
    """

    def __init__(
        self,
        settings: Settings,
        *,
        save_manager: Optional[SaveManager] = None,
        seed: Optional[int] = None,
        smoke_frames: Optional[int] = None,
    ) -> None:
        self.settings = settings

        super().__init__(
            width=settings.video.width,
            height=settings.video.height,
            title="Amor Mortuorum",
            fullscreen=settings.video.fullscreen,
            resizable=True,
            vsync=settings.video.vsync,
            center_window=True,
        )
        self.background_color = arcade.color.BLACK

        # Shared state
        save_manager = save_manager or SaveManager()
        self.state = GameContext(settings=settings, save_manager=save_manager, seed=seed)
        try:
            self.state.meta = save_manager.load_meta()
        except SaveError:
            logger.info("No existing meta save; starting fresh")
        self._load_game_data()

        # Managers
        self.scene_manager = SceneManager(self)
        self.input = InputManager(self, settings.input.mapping)

        # Smoke mode: run N frames then close (used by CI and --smoke)
        self._smoke_frames_left = smoke_frames

        # Boot into the first scene (late import keeps scene modules optional at import time)
        from .scenes.boot import BootScene

        self.scene_manager.push(BootScene(self))

        logger.info(
            "GameApp initialized: %dx%d fullscreen=%s vsync=%s",
            settings.video.width,
            settings.video.height,
            settings.video.fullscreen,
            settings.video.vsync,
        )

    def _load_game_data(self) -> None:
        """Load static game data if the data package exists (added in a later phase)."""
        try:
            from .data import GameData
        except ImportError:
            return
        self.state.data = GameData.load()

    # Arcade lifecycle
    def on_draw(self):  # noqa: N802 (arcade API)
        self.clear()
        self.scene_manager.draw()

    def on_update(self, delta_time: float):  # noqa: N802 (arcade API)
        self.scene_manager.update(delta_time)
        if self._smoke_frames_left is not None:
            self._smoke_frames_left -= 1
            if self._smoke_frames_left <= 0:
                logger.info("Smoke run complete; closing window")
                self.close()

    # Input events: delegate through InputManager, then to scene if not handled
    def on_key_press(self, key: int, modifiers: int):  # noqa: N802 (arcade API)
        actions = self.input.process_key_press(key, modifiers)
        handled = self.scene_manager.key_actions(actions, pressed=True)
        if not handled:
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
    def toggle_fullscreen(self, fullscreen: Optional[bool] = None) -> None:
        if fullscreen is None:
            fullscreen = not self.fullscreen
        self.set_fullscreen(fullscreen)
        logger.info("Fullscreen toggled: %s", fullscreen)
