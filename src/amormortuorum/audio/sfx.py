import json
import logging
import os
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union


logger = logging.getLogger("amormortuorum.audio.sfx")


class SFXEvent(str, Enum):
    """Core SFX events that the game can trigger.

    These are intentionally small and stable to keep the rest of the codebase
    decoupled from asset changes.
    """

    UI_CLICK = "ui_click"
    CHEST_OPEN = "chest_open"
    HIT = "hit"
    DEFEAT = "defeat"


@dataclass
class _SoundWrapper:
    """A thin wrapper around a backend sound object to normalize interface."""

    obj: Any

    def play(self, volume: float) -> None:
        # Most backends (arcade.Sound) support play(volume=...)
        try:
            play = getattr(self.obj, "play", None)
            if callable(play):
                # Some backends accept (volume=...), others positional
                try:
                    play(volume=volume)  # type: ignore[call-arg]
                except TypeError:
                    play(volume)  # type: ignore[misc]
        except Exception:  # noqa: BLE001
            logger.exception("SFX: sound backend raised while playing")


class SFXManager:
    """Service for loading and playing sound effects, optionally using Arcade.

    Key guarantees:
    - Graceful degradation: If backend or assets are missing, no exceptions
      escape public methods. Methods return False when playback did not occur.
    - Explicit API for core events that other systems can call without caring
      about audio presence or asset availability.

    Usage:
    - Provide a config mapping event keys to file paths (relative or absolute).
      Missing config or files are tolerated.
    - Or register sounds programmatically via register_sound / register_path.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        *,
        enabled: bool = True,
        volume: float = 1.0,
        backend: Optional[Any] = None,
        auto_load: bool = True,
    ) -> None:
        """Create a new SFX manager.

        Args:
            config_path: Optional path to a JSON mapping of event -> sound path.
            enabled: Whether playback is enabled.
            volume: Master SFX volume [0.0, 1.0].
            backend: Optional backend module (e.g., arcade). If None, manager
                     attempts to import arcade when needed. Tests can inject a
                     fake backend.
            auto_load: If True, loads config immediately (if provided).
        """
        self._lock = threading.RLock()
        self._enabled = bool(enabled)
        self._volume = self._clamp_volume(volume)
        self._backend = backend  # May be None; lazy import on demand
        self._config_path = config_path
        self._config: Dict[str, str] = {}
        self._sounds: Dict[str, _SoundWrapper] = {}

        if auto_load and config_path:
            self.reload()

    # ---------------------- Public properties ----------------------
    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        with self._lock:
            self._enabled = bool(value)

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        with self._lock:
            self._volume = self._clamp_volume(value)

    # ---------------------- Core API ----------------------
    def reload(self) -> None:
        """Reload configuration and sounds from the current config path.

        Missing or malformed configs are tolerated and only logged.
        """
        with self._lock:
            if not self._config_path:
                return
            try:
                self._config = self._load_config(self._config_path)
            except Exception:  # noqa: BLE001
                logger.exception("SFX: Failed to load config at %s", self._config_path)
                self._config = {}
            self._load_sounds_from_config()

    def play(self, event: Union[SFXEvent, str]) -> bool:
        """Attempt to play the SFX for the event. Returns True on success.

        This never raises; it logs and returns False on failure or when disabled.
        """
        key = str(event)
        with self._lock:
            if not self._enabled:
                logger.debug("SFX: Playback disabled (event=%s)", key)
                return False
            snd = self._sounds.get(key)
        if snd is None:
            logger.debug("SFX: No sound registered for event '%s'", key)
            return False
        try:
            snd.play(self._volume)
            return True
        except Exception:  # noqa: BLE001
            logger.exception("SFX: Unexpected error while playing '%s'", key)
            return False

    def register_sound(self, event: Union[SFXEvent, str], sound_obj: Any) -> None:
        """Register a pre-constructed backend sound object for an event."""
        key = str(event)
        with self._lock:
            self._sounds[key] = _SoundWrapper(sound_obj)
            logger.debug("SFX: Registered sound object for '%s'", key)

    def register_path(self, event: Union[SFXEvent, str], path: str) -> None:
        """Register a path and try to load an audio object via backend.

        Missing backend or file is tolerated; the event will simply not play.
        """
        key = str(event)
        try:
            wrapper = self._create_sound_wrapper(path)
        except Exception:  # noqa: BLE001
            wrapper = None
        with self._lock:
            if wrapper is not None:
                self._sounds[key] = wrapper
                logger.debug("SFX: Registered sound path for '%s' -> %s", key, path)
            else:
                # Keep as unregistered; play() will report not found.
                logger.info("SFX: Could not load sound for '%s' from '%s'", key, path)

    # ---------------------- Helpers ----------------------
    def _load_config(self, path: str) -> Dict[str, str]:
        if not os.path.exists(path):
            logger.warning("SFX: Config not found at %s (proceeding without SFX)", path)
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logger.exception("SFX: Config at %s is not valid JSON", path)
            return {}
        if not isinstance(data, dict):
            logger.warning("SFX: Config at %s must be an object mapping", path)
            return {}
        # Normalize keys to str
        return {str(k): str(v) for k, v in data.items()}

    def _load_sounds_from_config(self) -> None:
        # Don't raise if backend missing; just log and continue.
        for key, path in self._config.items():
            self.register_path(key, path)

    def _create_sound_wrapper(self, path: str) -> Optional[_SoundWrapper]:
        # Resolve path; allow relative to project root (cwd) or this file.
        resolved = path
        if not os.path.isabs(resolved):
            # Try relative to cwd first; if not exists, try relative to repo root
            if not os.path.exists(resolved):
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
                candidate = os.path.abspath(os.path.join(base, resolved))
                resolved = candidate
        if not os.path.exists(resolved):
            logger.info("SFX: Asset not found at %s", resolved)
            return None
        backend = self._ensure_backend()
        if backend is None:
            logger.info("SFX: No audio backend available; cannot load %s", resolved)
            return None
        try:
            # Arcade API: Sound(path, streaming=False)
            sound = backend.Sound(resolved, streaming=False)  # type: ignore[attr-defined]
            return _SoundWrapper(sound)
        except Exception:  # noqa: BLE001
            logger.exception("SFX: Backend failed to load %s", resolved)
            return None

    def _ensure_backend(self) -> Optional[Any]:
        if self._backend is not None:
            return self._backend
        # Lazy import arcade to avoid hard dependency if users do not want audio
        try:
            import importlib

            self._backend = importlib.import_module("arcade")
        except Exception:  # noqa: BLE001
            self._backend = None
            logger.debug("SFX: Arcade backend not available; running in silent mode")
        return self._backend

    @staticmethod
    def _clamp_volume(v: float) -> float:
        try:
            fv = float(v)
        except Exception:  # noqa: BLE001
            return 1.0
        return max(0.0, min(1.0, fv))


# ---------------------- Default singleton & shortcuts ----------------------
_default_manager: Optional[SFXManager] = None


def _default_config_path() -> Optional[str]:
    # Allow override via env var
    env = os.getenv("AMOR_AUDIO_SFX_CONFIG")
    if env:
        return env
    # Project default at configs/audio/sfx.json (relative to repo root)
    candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../configs/audio/sfx.json"))
    return candidate if os.path.exists(candidate) else None


def get_sfx_manager() -> SFXManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = SFXManager(config_path=_default_config_path(), auto_load=True)
    return _default_manager


def play_ui_click() -> bool:
    return get_sfx_manager().play(SFXEvent.UI_CLICK)


def play_chest_open() -> bool:
    return get_sfx_manager().play(SFXEvent.CHEST_OPEN)


def play_hit() -> bool:
    return get_sfx_manager().play(SFXEvent.HIT)


def play_defeat() -> bool:
    return get_sfx_manager().play(SFXEvent.DEFEAT)
