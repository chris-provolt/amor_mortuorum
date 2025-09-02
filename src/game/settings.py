from __future__ import annotations

import dataclasses
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Set

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover - fallback for older Pythons if needed
    tomllib = None  # type: ignore


logger = logging.getLogger(__name__)


# Event topics used for observer callbacks
TOPIC_WINDOW = "window"
TOPIC_AUDIO = "audio"
TOPIC_UI = "ui"
TOPIC_ALL = "all"


def _as_bool(value: Any) -> bool:
    """Interpret common truthy/falsey values into a bool.

    Accepts: True/False, 1/0, "true"/"false", "yes"/"no", "on"/"off" (case-insensitive),
    non-empty strings evaluate to True if not matched otherwise.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
        # Non-empty strings default to True to avoid silent misconfig.
        return True
    return bool(value)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


@dataclass
class Settings:
    """Runtime settings for windowing, audio, and UI toggles.

    Import this module and use the module-level SETTINGS singleton for application-wide configuration:

        from game.settings import SETTINGS
        if SETTINGS.fullscreen:
            ...

    The settings can be constructed/overridden from:
    - Environment variables (prefix: AM_)
    - A TOML config file (env AM_SETTINGS_FILE or configs/settings.toml if present)

    Observers can subscribe to topics (window, audio, ui, or all) to be notified when settings change.
    """

    # Window/display
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    vsync: bool = True

    # Audio volumes (0.0 - 1.0)
    master_volume: float = 0.8
    music_volume: float = 0.8
    sfx_volume: float = 0.8

    # UI / gameplay toggles
    show_minimap: bool = True
    fog_of_war: bool = True

    # Internal: observer callbacks per topic
    _observers: Dict[str, Set[Callable[["Settings"], None]]] = field(
        default_factory=lambda: {TOPIC_WINDOW: set(), TOPIC_AUDIO: set(), TOPIC_UI: set(), TOPIC_ALL: set()},
        init=False,
        repr=False,
    )

    # ------------------------ Properties ------------------------
    @property
    def effective_music_volume(self) -> float:
        return _clamp(self.master_volume, 0.0, 1.0) * _clamp(self.music_volume, 0.0, 1.0)

    @property
    def effective_sfx_volume(self) -> float:
        return _clamp(self.master_volume, 0.0, 1.0) * _clamp(self.sfx_volume, 0.0, 1.0)

    # ------------------------ Core API ------------------------
    def validate(self) -> None:
        """Validate and normalize settings to safe values."""
        if self.width <= 0 or self.height <= 0:
            logger.warning("Invalid window size %sx%s; resetting to 1280x720", self.width, self.height)
            self.width, self.height = 1280, 720
        self.master_volume = _clamp(float(self.master_volume), 0.0, 1.0)
        self.music_volume = _clamp(float(self.music_volume), 0.0, 1.0)
        self.sfx_volume = _clamp(float(self.sfx_volume), 0.0, 1.0)
        self.fullscreen = bool(self.fullscreen)
        self.vsync = bool(self.vsync)
        self.show_minimap = bool(self.show_minimap)
        self.fog_of_war = bool(self.fog_of_war)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "fullscreen": self.fullscreen,
            "vsync": self.vsync,
            "master_volume": self.master_volume,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "show_minimap": self.show_minimap,
            "fog_of_war": self.fog_of_war,
        }

    # ------------------------ Loading & Overrides ------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        allowed = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        obj = cls(**filtered)  # type: ignore[arg-type]
        obj.validate()
        return obj

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        env = env or os.environ
        mapping = {
            "AM_WIDTH": ("width", int),
            "AM_HEIGHT": ("height", int),
            "AM_FULLSCREEN": ("fullscreen", _as_bool),
            "AM_VSYNC": ("vsync", _as_bool),
            "AM_MASTER_VOLUME": ("master_volume", float),
            "AM_MUSIC_VOLUME": ("music_volume", float),
            "AM_SFX_VOLUME": ("sfx_volume", float),
            "AM_SHOW_MINIMAP": ("show_minimap", _as_bool),
            "AM_FOG_OF_WAR": ("fog_of_war", _as_bool),
        }
        out: Dict[str, Any] = {}
        for env_key, (field_name, caster) in mapping.items():
            if env_key in env and env[env_key] != "":
                try:
                    out[field_name] = caster(env[env_key])
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Invalid env for %s=%r: %s", env_key, env[env_key], exc)
        return out

    @classmethod
    def from_toml_file(cls, path: Path) -> Dict[str, Any]:
        if not path.exists():
            logger.debug("Settings file not found: %s", path)
            return {}
        if tomllib is None:
            logger.warning("tomllib not available; cannot read TOML settings file: %s", path)
            return {}
        try:
            with path.open("rb") as f:
                doc = tomllib.load(f)
        except Exception as exc:
            logger.error("Failed to read settings TOML %s: %s", path, exc)
            return {}
        # Flatten either top-level or under [window]/[audio]/[ui]
        flat: Dict[str, Any] = {}
        # Common sections
        if isinstance(doc, dict):
            # Section: window
            if isinstance(doc.get("window"), dict):
                flat.update({k: v for k, v in doc["window"].items()})
            # Section: audio
            if isinstance(doc.get("audio"), dict):
                flat.update({k: v for k, v in doc["audio"].items()})
            # Section: ui
            if isinstance(doc.get("ui"), dict):
                flat.update({k: v for k, v in doc["ui"].items()})
            # Also allow direct top-level keys
            for k, v in doc.items():
                if isinstance(v, dict):
                    continue
                flat[k] = v
        return flat

    @classmethod
    def discover_config_path(cls) -> Optional[Path]:
        # AM_SETTINGS_FILE can be absolute or relative
        env_path = os.environ.get("AM_SETTINGS_FILE")
        if env_path:
            return Path(env_path).expanduser().resolve()
        # Default: project configs/settings.toml if exists
        # Derive repo root as two parents up from this file (src/game/settings.py -> repo root)
        try:
            here = Path(__file__).resolve()
            repo_root = here.parents[2]  # <repo>/src/game/settings.py -> <repo>
        except Exception:
            repo_root = Path.cwd()
        default_path = repo_root / "configs" / "settings.toml"
        if default_path.exists():
            return default_path
        return None

    @classmethod
    def from_sources(
        cls,
        *,
        env: Optional[Dict[str, str]] = None,
        file_path: Optional[Path | str] = None,
    ) -> "Settings":
        # Order of precedence (lowest to highest): defaults < file < env
        data: Dict[str, Any] = {}
        # File
        chosen_path: Optional[Path] = None
        if file_path is not None:
            chosen_path = Path(file_path).expanduser().resolve()
        else:
            chosen_path = cls.discover_config_path()
        if chosen_path is not None:
            data.update(cls.from_toml_file(chosen_path))
        # Env
        data.update(cls.from_env(env))
        settings = cls(**data)  # type: ignore[arg-type]
        settings.validate()
        return settings

    # ------------------------ Observers ------------------------
    def subscribe(self, topic: str, callback: Callable[["Settings"], None]) -> None:
        if topic not in self._observers:
            raise ValueError(f"Unknown settings topic: {topic}")
        self._observers[topic].add(callback)

    def unsubscribe(self, topic: str, callback: Callable[["Settings"], None]) -> None:
        if topic in self._observers:
            self._observers[topic].discard(callback)

    def _notify(self, topics: Iterable[str]) -> None:
        notified: Set[Callable[["Settings"], None]] = set()
        for topic in set(topics) | {TOPIC_ALL}:
            for cb in self._observers.get(topic, ()):  # type: ignore[arg-type]
                if cb in notified:
                    continue
                try:
                    cb(self)
                except Exception:
                    logger.exception("Settings observer failed for topic '%s'", topic)
                notified.add(cb)

    # ------------------------ Mutations ------------------------
    def update(self, **changes: Any) -> None:
        """Update settings in place, validate, and notify relevant topics.

        Only provided fields are changed. Observers are notified for the minimal set of topics.
        """
        if not changes:
            return

        before = self.as_dict()
        allowed = set(before.keys())
        for k, v in changes.items():
            if k not in allowed:
                raise AttributeError(f"Unknown settings field: {k}")
            setattr(self, k, v)
        self.validate()

        topics: Set[str] = set()
        if any(before[k] != getattr(self, k) for k in ("width", "height", "fullscreen", "vsync")):
            topics.add(TOPIC_WINDOW)
        if any(before[k] != getattr(self, k) for k in ("master_volume", "music_volume", "sfx_volume")):
            topics.add(TOPIC_AUDIO)
        if any(before[k] != getattr(self, k) for k in ("show_minimap", "fog_of_war")):
            topics.add(TOPIC_UI)
        if topics:
            self._notify(topics)

    # ------------------------ Integration Helpers ------------------------
    def apply_to_window(self, window: Any) -> None:
        """Apply window-related settings to an Arcade-like window object.

        This method is defensive and only calls methods if the window exposes them.
        - fullscreen: uses window.set_fullscreen(True/False) if available; else assigns .fullscreen
        - vsync: uses window.set_vsync(True/False) if available; else assigns .vsync
        - size: uses window.set_size(width, height) if available; else assigns .width/.height if present
        """
        # Fullscreen
        try:
            if hasattr(window, "set_fullscreen") and callable(getattr(window, "set_fullscreen")):
                window.set_fullscreen(bool(self.fullscreen))
            elif hasattr(window, "fullscreen"):
                setattr(window, "fullscreen", bool(self.fullscreen))
        except Exception:
            logger.exception("Failed applying fullscreen=%s to window", self.fullscreen)

        # VSync (note: some frameworks only allow during window creation)
        try:
            if hasattr(window, "set_vsync") and callable(getattr(window, "set_vsync")):
                window.set_vsync(bool(self.vsync))
            elif hasattr(window, "vsync"):
                setattr(window, "vsync", bool(self.vsync))
        except Exception:
            logger.exception("Failed applying vsync=%s to window", self.vsync)

        # Size
        try:
            if hasattr(window, "set_size") and callable(getattr(window, "set_size")):
                window.set_size(int(self.width), int(self.height))
            else:
                if hasattr(window, "width"):
                    setattr(window, "width", int(self.width))
                if hasattr(window, "height"):
                    setattr(window, "height", int(self.height))
        except Exception:
            logger.exception("Failed applying size %sx%s to window", self.width, self.height)

    def apply_to_audio(self, audio_system: Any) -> None:
        """Apply audio settings to an audio/mixer system.

        Expected interface (any subset is applied if available):
          - set_master_volume(float)
          - set_music_volume(float)
          - set_sfx_volume(float)
        """
        try:
            if hasattr(audio_system, "set_master_volume"):
                audio_system.set_master_volume(float(self.master_volume))
            if hasattr(audio_system, "set_music_volume"):
                audio_system.set_music_volume(float(self.effective_music_volume))
            if hasattr(audio_system, "set_sfx_volume"):
                audio_system.set_sfx_volume(float(self.effective_sfx_volume))
        except Exception:
            logger.exception("Failed applying audio settings to audio system")


def _build_default_settings() -> Settings:
    return Settings.from_sources()


# Module-level singleton used by the rest of the app.
SETTINGS: Settings = _build_default_settings()

__all__ = [
    "Settings",
    "SETTINGS",
    "TOPIC_WINDOW",
    "TOPIC_AUDIO",
    "TOPIC_UI",
    "TOPIC_ALL",
]
