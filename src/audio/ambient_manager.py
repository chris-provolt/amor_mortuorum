from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .interfaces import IAudioBackend
from ..config.audio_settings import AudioSettings
from ..core.scenes import SceneType


logger = logging.getLogger(__name__)


class AmbientManager:
    """Handles ambient background music per scene with volume control.

    Responsibilities:
    - Maintain a mapping of SceneType -> track path
    - Start/stop looping playback for the active scene
    - Apply volume derived from AudioSettings (master * music)
    - React to scene changes idempotently

    This class is designed to be driven by the game state controller:
      ambient.on_scene_changed(SceneType.DUNGEON)

    Note: For production use, integrate this with your scene management system
    or event bus to call on_scene_changed when the active scene changes.
    """

    def __init__(
        self,
        backend: IAudioBackend,
        settings: AudioSettings,
        track_map: Dict[SceneType, Optional[str]],
    ) -> None:
        self._backend = backend
        self._settings = settings
        self._track_map: Dict[SceneType, Optional[str]] = dict(track_map)
        self._enabled: bool = True

        self._current_scene: Optional[SceneType] = None
        self._current_track: Optional[str] = None
        self._current_player: Optional[Any] = None

        # If disabled while a scene switch happens, we remember the last requested scene
        # so we can resume when re-enabled.
        self._pending_scene: Optional[SceneType] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        if not enabled:
            self._stop_current()
        else:
            # Resume if we had a pending scene request
            if self._pending_scene is not None:
                scene = self._pending_scene
                self._pending_scene = None
                self.on_scene_changed(scene)

    def update_track_map(self, track_map: Dict[SceneType, Optional[str]]) -> None:
        """Replace the track map at runtime (e.g., for modding or platform-specific paths)."""
        self._track_map = dict(track_map)
        # Re-evaluate current scene mapping
        if self._current_scene is not None:
            self.on_scene_changed(self._current_scene)

    def update_settings(self, settings: AudioSettings) -> None:
        """Replace settings object and re-apply volume."""
        self._settings = settings
        self.refresh_volume()

    def on_scene_changed(self, scene: SceneType) -> None:
        """Handle scene change and update ambient track as needed."""
        if not isinstance(scene, SceneType):
            raise ValueError(f"Invalid scene type: {scene}")

        if not self._enabled:
            self._pending_scene = scene
            logger.debug("Ambient disabled; scene %s stored as pending", scene)
            return

        if self._current_scene == scene:
            # Already playing for this scene; nothing to do.
            logger.debug("Ambient already set for scene %s; skipping", scene)
            return

        track = self._track_map.get(scene)
        self._switch_to_track(scene, track)

    def refresh_volume(self) -> None:
        """Re-apply volume to the current ambient track from settings."""
        if not self._current_player:
            return
        volume = self._compute_volume()
        try:
            self._backend.set_player_volume(self._current_player, volume)
            logger.debug("Ambient volume updated to %.3f", volume)
        except Exception as exc:
            logger.exception("Failed to set ambient volume: %s", exc)

    def stop(self) -> None:
        """Stop any playing ambient track and clear state."""
        self._pending_scene = None
        self._stop_current()
        self._current_scene = None
        self._current_track = None

    # ----- Internals -----

    def _compute_volume(self) -> float:
        v = self._settings.effective_music_volume
        # Double clamp to be extra safe
        return max(0.0, min(1.0, float(v)))

    def _switch_to_track(self, scene: SceneType, track_path: Optional[str]) -> None:
        # Stop previous if present
        self._stop_current()

        self._current_scene = scene
        self._current_track = track_path

        if not track_path:
            logger.info("No ambient track configured for scene %s; ambient stopped", scene)
            return

        volume = self._compute_volume()
        try:
            self._current_player = self._backend.start_music(track_path, volume=volume, loop=True)
            logger.info("Ambient started: scene=%s track=%s volume=%.3f", scene, track_path, volume)
        except Exception as exc:
            self._current_player = None
            logger.exception("Failed to start ambient track '%s' for scene %s: %s", track_path, scene, exc)

    def _stop_current(self) -> None:
        if not self._current_player:
            return
        try:
            self._backend.stop_music(self._current_player)
            logger.info("Ambient stopped: scene=%s track=%s", self._current_scene, self._current_track)
        except Exception as exc:
            logger.exception("Failed to stop ambient track: %s", exc)
        finally:
            self._current_player = None
