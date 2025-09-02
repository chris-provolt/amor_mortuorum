from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    # Optional: Arcade is only used at runtime; tests can run without it
    import arcade  # type: ignore
except Exception:  # pragma: no cover - arcade not required for tests
    arcade = None  # type: ignore

try:
    from platformdirs import user_config_dir
except Exception:  # pragma: no cover
    # Fallback if platformdirs is unavailable at runtime (should be installed)
    def user_config_dir(appname: str, appauthor: Optional[str] = None) -> str:
        return str(Path.home() / f".{appname}")


log = logging.getLogger(__name__)


@dataclass
class AudioSettings:
    master_volume: float = 1.0  # 0..1
    music_volume: float = 0.8   # 0..1
    sfx_volume: float = 0.8     # 0..1
    muted: bool = False


@dataclass
class VideoSettings:
    fullscreen: bool = False
    vsync: bool = True
    resolution: str = "1280x720"  # WxH string; stub for now


@dataclass
class ControlsSettings:
    # Stub mappings; actual in-game bindings to be implemented later
    move_up: str = "W"
    move_down: str = "S"
    move_left: str = "A"
    move_right: str = "D"
    action: str = "SPACE"


@dataclass
class GameSettings:
    audio: AudioSettings = field(default_factory=AudioSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    controls: ControlsSettings = field(default_factory=ControlsSettings)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize settings to a JSON-friendly dict."""
        return {
            "audio": asdict(self.audio),
            "video": asdict(self.video),
            "controls": asdict(self.controls),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GameSettings":
        """Create settings from a dict with validation and clamping."""
        audio = d.get("audio", {})
        video = d.get("video", {})
        controls = d.get("controls", {})
        gs = cls(
            audio=AudioSettings(
                master_volume=_clamp(audio.get("master_volume", 1.0), 0.0, 1.0),
                music_volume=_clamp(audio.get("music_volume", 0.8), 0.0, 1.0),
                sfx_volume=_clamp(audio.get("sfx_volume", 0.8), 0.0, 1.0),
                muted=bool(audio.get("muted", False)),
            ),
            video=VideoSettings(
                fullscreen=bool(video.get("fullscreen", False)),
                vsync=bool(video.get("vsync", True)),
                resolution=str(video.get("resolution", "1280x720")),
            ),
            controls=ControlsSettings(
                move_up=str(controls.get("move_up", "W")),
                move_down=str(controls.get("move_down", "S")),
                move_left=str(controls.get("move_left", "A")),
                move_right=str(controls.get("move_right", "D")),
                action=str(controls.get("action", "SPACE")),
            ),
        )
        return gs


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(val)))


class SettingsRuntimeAdapter:
    """Adapter for applying settings to the live runtime.

    Default implementation integrates with arcade when available. For tests,
    a fake adapter can be supplied to capture calls.
    """

    def __init__(self) -> None:
        self._window_ref = None

    def bind_window(self, window: Any) -> None:  # type: ignore[valid-type]
        self._window_ref = window

    def set_master_volume(self, volume: float) -> None:
        if arcade is not None:
            try:
                arcade.set_sound_volume(volume)
            except Exception:  # pragma: no cover - depends on arcade
                log.debug("arcade.set_sound_volume not available")

    def set_music_volume(self, volume: float) -> None:
        # Placeholder: actual mixer/channel routing would be applied here
        pass

    def set_sfx_volume(self, volume: float) -> None:
        # Placeholder
        pass

    def set_muted(self, muted: bool) -> None:
        if muted:
            self.set_master_volume(0.0)
        else:
            # no-op here; master volume will be applied by apply_all
            pass

    def set_fullscreen(self, fullscreen: bool) -> None:
        if self._window_ref is not None:
            try:
                self._window_ref.set_fullscreen(fullscreen)
            except Exception:  # pragma: no cover
                log.warning("Failed to set fullscreen on window")

    def set_vsync(self, vsync: bool) -> None:
        # VSync control may depend on context; left as stub
        pass

    def set_resolution(self, resolution: str) -> None:
        if self._window_ref is not None:
            try:
                w, h = map(int, resolution.lower().split("x"))
                self._window_ref.set_size(w, h)
            except Exception:  # pragma: no cover
                log.warning("Failed to set resolution: %s", resolution)

    def apply_all(self, settings: GameSettings) -> None:
        self.set_fullscreen(settings.video.fullscreen)
        self.set_vsync(settings.video.vsync)
        self.set_resolution(settings.video.resolution)
        if settings.audio.muted:
            self.set_muted(True)
        else:
            self.set_master_volume(settings.audio.master_volume)
            self.set_music_volume(settings.audio.music_volume)
            self.set_sfx_volume(settings.audio.sfx_volume)


class SettingsManager:
    """Manage loading, saving, and applying game settings.

    - Persists settings to a JSON file under the user config directory
    - Notifies observers on change
    - Applies settings to the runtime via an adapter
    """

    def __init__(
        self,
        app_name: str = "AmorMortuorum",
        config_dir: Optional[Path] = None,
        runtime_adapter: Optional[SettingsRuntimeAdapter] = None,
    ) -> None:
        self.app_name = app_name
        self.config_dir = Path(config_dir) if config_dir else Path(user_config_dir(appname=app_name))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.config_dir / "settings.json"
        self._settings = GameSettings()
        self._observers: list[Callable[[GameSettings], None]] = []
        self.adapter = runtime_adapter or SettingsRuntimeAdapter()

        if self.settings_file.exists():
            self.load()
        else:
            self.save()  # write defaults

    @property
    def settings(self) -> GameSettings:
        return self._settings

    def subscribe(self, callback: Callable[[GameSettings], None]) -> None:
        self._observers.append(callback)

    def _notify(self) -> None:
        for cb in list(self._observers):
            try:
                cb(self._settings)
            except Exception:  # pragma: no cover - observers are external
                log.exception("Settings observer failed")

    def load(self) -> None:
        try:
            content = json.loads(self.settings_file.read_text(encoding="utf-8"))
            self._settings = GameSettings.from_dict(content)
            log.info("Settings loaded from %s", self.settings_file)
        except Exception:
            log.exception("Failed to load settings; using defaults")
            self._settings = GameSettings()
        # Apply on load
        self.apply()

    def save(self) -> None:
        try:
            self.settings_file.write_text(json.dumps(self._settings.to_dict(), indent=2), encoding="utf-8")
            log.info("Settings saved to %s", self.settings_file)
        except Exception:
            log.exception("Failed to save settings")

    def apply(self) -> None:
        """Apply current settings to runtime via adapter."""
        try:
            self.adapter.apply_all(self._settings)
        except Exception:  # pragma: no cover - platform/runtime dependent
            log.exception("Failed to apply settings to runtime")

    # Convenience setters that validate/clamp and apply incrementally
    def set_audio(self, *, master_volume: Optional[float] = None, music_volume: Optional[float] = None,
                  sfx_volume: Optional[float] = None, muted: Optional[bool] = None) -> None:
        if master_volume is not None:
            self._settings.audio.master_volume = _clamp(master_volume, 0.0, 1.0)
            self.adapter.set_master_volume(self._settings.audio.master_volume)
        if music_volume is not None:
            self._settings.audio.music_volume = _clamp(music_volume, 0.0, 1.0)
            self.adapter.set_music_volume(self._settings.audio.music_volume)
        if sfx_volume is not None:
            self._settings.audio.sfx_volume = _clamp(sfx_volume, 0.0, 1.0)
            self.adapter.set_sfx_volume(self._settings.audio.sfx_volume)
        if muted is not None:
            self._settings.audio.muted = bool(muted)
            self.adapter.set_muted(self._settings.audio.muted)
        self.save()
        self._notify()

    def set_video(self, *, fullscreen: Optional[bool] = None, vsync: Optional[bool] = None,
                  resolution: Optional[str] = None) -> None:
        if fullscreen is not None:
            self._settings.video.fullscreen = bool(fullscreen)
            self.adapter.set_fullscreen(self._settings.video.fullscreen)
        if vsync is not None:
            self._settings.video.vsync = bool(vsync)
            self.adapter.set_vsync(self._settings.video.vsync)
        if resolution is not None:
            self._settings.video.resolution = str(resolution)
            self.adapter.set_resolution(self._settings.video.resolution)
        self.save()
        self._notify()

    def set_control(self, action: str, key: str) -> None:
        if not hasattr(self._settings.controls, action):
            raise ValueError(f"Unknown control action: {action}")
        setattr(self._settings.controls, action, str(key))
        self.save()
        self._notify()
