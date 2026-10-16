"""Audio: named sound-effect hooks and music loops with volume settings.

Real assets go in ``amormortuorum/resources/audio/<name>.wav`` and take
priority. When a name has no asset, the effect or track is rendered once by
the game's own chiptune synthesizer (:mod:`.chiptune`) into a cache
directory, so the game is never silent and no binary assets need to live in
the repo. Rendering is quick (a few seconds for the whole soundtrack) and
happens in a background thread at start-up; anything requested before it is
ready is rendered on the spot.

Everything is guarded: if the audio driver is missing (headless CI) the
manager silently disables itself.
"""
from __future__ import annotations

import logging
import os
import threading
import wave
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import chiptune
from .chiptune import SAMPLE_RATE

logger = logging.getLogger(__name__)

CACHE_VERSION = "v2"  # bump when the synthesizer or any definition changes

# The effect and track names the game can ask for (see chiptune for the content)
PLACEHOLDER_SFX = chiptune.SFX
PLACEHOLDER_MUSIC = chiptune.MUSIC


def _write_wav(path: Path, pcm) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    os.replace(tmp, path)


def synthesize_sfx(name: str, path: Path) -> Path:
    """Render the effect ``name`` to ``path`` and return it."""
    _write_wav(path, chiptune.render_sfx(name))
    return path


def synthesize_music(name: str, path: Path) -> Path:
    """Render the looping track ``name`` to ``path`` and return it."""
    _write_wav(path, chiptune.render_track(chiptune.MUSIC[name]))
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
        self.cache_dir = Path(cache_dir) / CACHE_VERSION
        self._loader = loader
        self._sounds: Dict[str, Any] = {}
        self._synth_lock = threading.Lock()
        self._prewarm_thread: Optional[threading.Thread] = None
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

    # Rendering

    def prewarm(self) -> None:
        """Render every track and effect that is not cached yet, in the background."""
        if not self.enabled or self._prewarm_thread is not None:
            return

        def work() -> None:
            for name in list(PLACEHOLDER_MUSIC) + list(PLACEHOLDER_SFX):
                try:
                    self._path_for(name, music=name in PLACEHOLDER_MUSIC)
                except Exception as e:  # pragma: no cover - disk trouble
                    logger.warning("Could not render %s: %s", name, e)

        self._prewarm_thread = threading.Thread(target=work, name="audio-prewarm", daemon=True)
        self._prewarm_thread.start()

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
            with self._synth_lock:
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

    def play(self, name: str, *, speed: float = 1.0) -> bool:
        """Play effect ``name`` at the SFX volume, optionally re-pitched by ``speed``
        (1.0 = as rendered). Returns whether anything played."""
        if not self.enabled or self.sfx_volume <= 0:
            return False
        sound = self._sound(name)
        if sound is None:
            return False
        try:
            if speed != 1.0:
                sound.play(volume=self.sfx_volume, speed=speed)
            else:
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

    def play(self, name: str, *, speed: float = 1.0) -> bool:
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
    "CACHE_VERSION",
]
