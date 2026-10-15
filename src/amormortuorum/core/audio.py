"""Audio: named sound-effect hooks and ambient loops with volume settings.

Real assets go in ``amormortuorum/resources/audio/<name>.wav`` and take
priority. When a name has no asset, a small placeholder tone is synthesized
once into a cache directory with the standard library, so the game is never
silent and no binary assets need to live in the repo.

Everything is guarded: if the audio driver is missing (headless CI) the
manager silently disables itself.
"""
from __future__ import annotations

import logging
import math
import os
import struct
import wave
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

SAMPLE_RATE = 22050

# name -> list of (frequency_hz, seconds, shape) segments; shape: "sine" | "square" | "noise"
PLACEHOLDER_SFX: Dict[str, List[Tuple[float, float, str]]] = {
    "menu_move": [(660, 0.03, "square")],
    "menu_confirm": [(523, 0.05, "square"), (784, 0.07, "square")],
    "menu_back": [(392, 0.06, "square")],
    "step": [(110, 0.02, "noise")],
    "chest": [(659, 0.06, "sine"), (880, 0.06, "sine"), (1175, 0.1, "sine")],
    "gold": [(1318, 0.04, "square"), (1568, 0.06, "square")],
    "hit": [(180, 0.05, "noise"), (90, 0.05, "square")],
    "heal": [(523, 0.07, "sine"), (659, 0.07, "sine"), (784, 0.1, "sine")],
    "victory": [(523, 0.08, "square"), (659, 0.08, "square"), (784, 0.08, "square"),
                (1046, 0.2, "square")],
    "defeat": [(392, 0.15, "sine"), (311, 0.15, "sine"), (233, 0.3, "sine")],
    "level_up": [(784, 0.06, "sine"), (988, 0.06, "sine"), (1318, 0.15, "sine")],
    "relic": [(880, 0.1, "sine"), (1108, 0.1, "sine"), (1318, 0.1, "sine"), (1760, 0.25, "sine")],
    "door": [(140, 0.12, "noise"), (200, 0.08, "square")],
    "trap": [(1200, 0.03, "noise"), (160, 0.12, "square")],
    "stairs": [(330, 0.08, "sine"), (262, 0.08, "sine"), (196, 0.12, "sine")],
    "portal": [(440, 0.08, "sine"), (554, 0.08, "sine"), (659, 0.08, "sine"), (880, 0.2, "sine")],
    "boss": [(110, 0.25, "square"), (104, 0.25, "square"), (98, 0.4, "square")],
    "flee": [(600, 0.04, "square"), (500, 0.04, "square"), (400, 0.06, "square")],
}

# name -> (base frequency, seconds) ambient drone loops
PLACEHOLDER_MUSIC: Dict[str, Tuple[float, float]] = {
    "graveyard": (55.0, 6.0),
    "dungeon": (41.2, 6.0),
    "combat": (73.4, 4.0),
}


def _segment_samples(freq: float, seconds: float, shape: str, seed: int) -> List[int]:
    n = int(SAMPLE_RATE * seconds)
    out: List[int] = []
    state = seed or 1
    for i in range(n):
        t = i / SAMPLE_RATE
        env = min(1.0, (n - i) / max(1, n * 0.3))  # quick fade-out to avoid clicks
        if shape == "square":
            v = 0.5 if math.sin(2 * math.pi * freq * t) >= 0 else -0.5
        elif shape == "noise":
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            v = (state / 0x7FFFFFFF) * 1.2 - 0.6
        else:
            v = math.sin(2 * math.pi * freq * t) * 0.7
        out.append(int(v * env * 12000))
    return out


def _write_wav(path: Path, samples: Iterable[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(struct.pack("<h", max(-32768, min(32767, s))) for s in samples)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)


def synthesize_sfx(name: str, path: Path) -> Path:
    """Write the placeholder effect ``name`` to ``path`` and return it."""
    segments = PLACEHOLDER_SFX[name]
    samples: List[int] = []
    for i, (freq, seconds, shape) in enumerate(segments):
        samples.extend(_segment_samples(freq, seconds, shape, seed=hash(name) % 9973 + i))
    _write_wav(path, samples)
    return path


def synthesize_music(name: str, path: Path) -> Path:
    """Write a seamless low drone for ``name`` (two detuned sines over a slow pulse)."""
    base, seconds = PLACEHOLDER_MUSIC[name]
    n = int(SAMPLE_RATE * seconds)
    samples: List[int] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        pulse = 0.65 + 0.35 * math.sin(2 * math.pi * t / seconds)  # one full cycle: loops cleanly
        v = (math.sin(2 * math.pi * base * t) + 0.6 * math.sin(2 * math.pi * base * 1.5 * t)) * 0.3
        samples.append(int(v * pulse * 9000))
    _write_wav(path, samples)
    return path


def asset_path(name: str) -> Optional[Path]:
    """A packaged ``resources/audio/<name>.wav`` if one ships with the game."""
    try:
        candidate = resources.files("amormortuorum.resources.audio").joinpath(f"{name}.wav")
        if candidate.is_file():
            return Path(str(candidate))
    except (ModuleNotFoundError, TypeError, OSError):
        return None
    return None


class AudioManager:
    """Plays named effects and ambient loops; volumes come from ``AudioSettings``.

    ``loader`` turns a path into an object with ``play(volume=..., loop=...)``
    returning a player with ``pause()``/``delete()``; by default ``arcade.Sound``.
    Pass a stub in tests.
    """

    def __init__(
        self,
        settings,
        cache_dir: Path,
        *,
        loader: Optional[Callable[[Path], Any]] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.settings = settings
        self.cache_dir = Path(cache_dir)
        self._loader = loader
        self._sounds: Dict[str, Any] = {}
        self._music_player: Any = None
        self.current_music: Optional[str] = None
        if enabled is None:
            enabled = os.environ.get("ARCADE_HEADLESS", "").lower() not in ("1", "true")
        self.enabled = enabled
        if self._loader is None and self.enabled:
            try:
                import arcade

                self._loader = lambda path: arcade.Sound(path)
            except Exception as e:  # pragma: no cover - depends on the host
                logger.warning("Audio unavailable: %s", e)
                self.enabled = False

    # Volumes

    @property
    def sfx_volume(self) -> float:
        return max(0.0, min(1.0, float(self.settings.audio.sfx_volume)))

    @property
    def music_volume(self) -> float:
        return max(0.0, min(1.0, float(self.settings.audio.music_volume)))

    def apply_volumes(self) -> None:
        """Re-apply the music volume to the running loop (SFX read it per play)."""
        player = self._music_player
        if player is not None:
            try:
                player.volume = self.music_volume
            except Exception:  # pragma: no cover
                pass

    # Lookup

    def _path_for(self, name: str, music: bool = False) -> Optional[Path]:
        packaged = asset_path(name)
        if packaged is not None:
            return packaged
        table = PLACEHOLDER_MUSIC if music else PLACEHOLDER_SFX
        if name not in table:
            return None
        path = self.cache_dir / ("music" if music else "sfx") / f"{name}.wav"
        if not path.exists():
            (synthesize_music if music else synthesize_sfx)(name, path)
        return path

    def _sound(self, name: str, music: bool = False) -> Any:
        key = ("music:" if music else "sfx:") + name
        if key in self._sounds:
            return self._sounds[key]
        path = self._path_for(name, music=music)
        if path is None or self._loader is None:
            self._sounds[key] = None
            return None
        try:
            sound = self._loader(path)
        except Exception as e:  # pragma: no cover - driver specific
            logger.warning("Could not load sound %s: %s", name, e)
            sound = None
        self._sounds[key] = sound
        return sound

    # Playback

    def play(self, name: str) -> bool:
        """Play effect ``name`` at the SFX volume. Returns whether anything played."""
        if not self.enabled or self.sfx_volume <= 0:
            return False
        sound = self._sound(name)
        if sound is None:
            return False
        try:
            sound.play(volume=self.sfx_volume)
        except Exception as e:  # pragma: no cover - driver specific
            logger.debug("sfx %s failed: %s", name, e)
            return False
        return True

    def play_music(self, name: Optional[str]) -> None:
        """Loop the ambient track ``name`` (None stops music). No-op if already playing."""
        if name == self.current_music:
            self.apply_volumes()
            return
        self.stop_music()
        if name is None or not self.enabled:
            return
        sound = self._sound(name, music=True)
        if sound is None:
            return
        try:
            self._music_player = sound.play(volume=self.music_volume, loop=True)
            self.current_music = name
        except Exception as e:  # pragma: no cover
            logger.debug("music %s failed: %s", name, e)

    def stop_music(self) -> None:
        player = self._music_player
        self._music_player = None
        self.current_music = None
        if player is not None:
            try:
                player.pause()
                player.delete()
            except Exception:  # pragma: no cover
                pass


class NullAudio:
    """Drop-in that does nothing (used when a scene is built without an app audio)."""

    enabled = False
    current_music = None

    def play(self, name: str) -> bool:
        return False

    def play_music(self, name: Optional[str]) -> None:
        pass

    def stop_music(self) -> None:
        pass

    def apply_volumes(self) -> None:
        pass


__all__ = [
    "AudioManager",
    "NullAudio",
    "PLACEHOLDER_SFX",
    "PLACEHOLDER_MUSIC",
    "synthesize_sfx",
    "synthesize_music",
    "asset_path",
]
