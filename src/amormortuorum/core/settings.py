from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class VideoSettings:
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    vsync: bool = True
    ui_scale: float = 1.0


@dataclass
class AudioSettings:
    music_volume: float = 0.6
    sfx_volume: float = 0.8


@dataclass
class InputSettings:
    mapping: Dict[str, Iterable[str]] = field(default_factory=dict)


@dataclass
class Settings:
    video: VideoSettings = field(default_factory=VideoSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    input: InputSettings = field(default_factory=InputSettings)

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @classmethod
    def _deep_merge(cls, base: dict, overlay: dict) -> dict:
        merged = dict(base)
        for k, v in (overlay or {}).items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                merged[k] = cls._deep_merge(base[k], v)
            else:
                merged[k] = v
        return merged

    @classmethod
    def _from_dict(cls, data: dict) -> "Settings":
        video = VideoSettings(**data.get("video", {}))
        audio = AudioSettings(**data.get("audio", {}))
        input_ = InputSettings(mapping=data.get("input", {}).get("mapping", {}))
        return Settings(video=video, audio=audio, input=input_)

    @classmethod
    def load(cls, user_path: Optional[Path] = None) -> "Settings":
        """Load settings from built-in defaults and optional user override file.

        If user_path is provided and exists, overlay values onto defaults.
        """
        # Load default YAML from package resources
        try:
            with resources.files("amormortuorum.config").joinpath("default_settings.yaml").open("r", encoding="utf-8") as f:
                default_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("Default settings not found; falling back to dataclass defaults.")
            default_data = dataclasses.asdict(Settings())

        user_data = {}
        if user_path is not None:
            if user_path.exists():
                user_data = cls._load_yaml(user_path)
                logger.info("Loaded user settings from %s", user_path)
            else:
                logger.warning("User settings file not found: %s", user_path)

        merged = cls._deep_merge(default_data, user_data)
        settings = cls._from_dict(merged)
        logger.debug("Settings merged: %s", settings)
        return settings

    def save(self, path: Path) -> None:
        data = {
            "video": dataclasses.asdict(self.video),
            "audio": dataclasses.asdict(self.audio),
            "input": {"mapping": {k: list(v) for k, v in self.input.mapping.items()}},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        logger.info("Saved settings to %s", path)
