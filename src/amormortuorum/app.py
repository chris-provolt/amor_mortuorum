from __future__ import annotations

import logging
import os
from typing import List, Optional

import arcade

from .core.audio import AudioManager
from .core.context import GameContext
from .core.controller import ControllerInput
from .core.input import InputManager
from .core.scenes.manager import SceneManager
from .core.settings import Settings
from .persistence import SaveError, SaveManager
from .ui.theme import set_ui_scale

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
        set_ui_scale(settings.video.ui_scale)

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
        self.audio = AudioManager(
            settings,
            save_manager.root_dir / "cache" / "audio",
            enabled=False if os.environ.get("AMOR_MUTE") == "1" else None,
        )
        self.audio.prewarm()
        self.controller = ControllerInput(self.dispatch_actions)
        if not self.smoke_mode_env():
            self.controller.start()

        # Smoke mode: run N frames then close (used by CI and --smoke). Scenes
        # consult ``app.smoke`` to auto-advance (start a run, enter the dungeon).
        self._smoke_frames_left = smoke_frames
        self.smoke = smoke_frames is not None

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

    def switch_profile(self, profile_id: str) -> None:
        """Point the game at another save profile (new or existing) and reload meta."""
        from .persistence import MetaState

        old = self.state.save_manager
        self.state.save_manager = SaveManager(root_dir=old.root_dir, profile_id=profile_id)
        try:
            self.state.meta = self.state.save_manager.load_meta()
        except SaveError:
            self.state.meta = MetaState()
        self.state.run = None
        self.settings.game.profile = profile_id
        logger.info("Switched to profile %r", profile_id)

    @staticmethod
    def smoke_mode_env() -> bool:
        return os.environ.get("ARCADE_HEADLESS", "").lower() in ("1", "true")

    def dispatch_actions(self, actions: List[str]) -> bool:
        """Feed logical actions (from keys or a controller) to the active scene."""
        return self.scene_manager.key_actions(list(actions), pressed=True)

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
        # pyglet can dispatch a resize while the window is still being constructed
        manager = getattr(self, "scene_manager", None)
        if manager is not None:
            manager.resize(width, height)

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
