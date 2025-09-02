from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class TrackPlayer(Protocol):
    """Protocol defining the minimum controls a track player must implement.

    Implementations should be lightweight wrappers around the underlying audio
    library's player object (e.g., pyglet via Arcade) so that they can be
    controlled deterministically and unit-tested with a Fake implementation.
    """

    def play(self, *, loop: bool = True) -> None:
        """Begin playback. If already playing, call should be idempotent."""

    def stop(self) -> None:
        """Stop playback and release any resources if applicable."""

    def set_volume(self, volume: float) -> None:
        """Set volume 0.0..1.0. Implementations must clamp to this range."""

    def get_volume(self) -> float:
        """Return the current effective volume, clamped to 0..1."""

    def is_playing(self) -> bool:
        """Return True if currently playing, False otherwise."""


# ---------------------------
# Fake (Test) Implementation
# ---------------------------


@dataclass
class FakeTrackPlayer:
    """A deterministic, dependency-free TrackPlayer implementation for tests.

    - Maintains simple state for play/stop and volume
    - No real audio playback occurs
    """

    name: str
    loop: bool = True
    _playing: bool = False
    _volume: float = 0.0

    def play(self, *, loop: bool = True) -> None:  # type: ignore[override]
        self.loop = loop
        self._playing = True
        # Do not mutate volume here to avoid pops; callers control volume via fades

    def stop(self) -> None:  # type: ignore[override]
        self._playing = False

    def set_volume(self, volume: float) -> None:  # type: ignore[override]
        if volume != volume:  # NaN check
            volume = 0.0
        self._volume = max(0.0, min(1.0, float(volume)))

    def get_volume(self) -> float:  # type: ignore[override]
        return self._volume

    def is_playing(self) -> bool:  # type: ignore[override]
        return self._playing


@dataclass
class FakeAudioEngine:
    """Factory for FakeTrackPlayer used in tests and headless runs."""

    created: dict[str, FakeTrackPlayer] = field(default_factory=dict)

    def load_track(self, name: str) -> FakeTrackPlayer:
        """Create or retrieve a FakeTrackPlayer by name.

        In production code, this would load a file. Here, it's name-only.
        """
        if name not in self.created:
            self.created[name] = FakeTrackPlayer(name=name)
        return self.created[name]


# -----------------------------
# Arcade/Pyglet Implementation
# -----------------------------


class ArcadeTrackPlayer:
    """Track player backed by arcade.Sound/pyglet Player (optional dependency).

    This class is imported at runtime only if arcade is available. Tests use
    FakeTrackPlayer and do not require arcade.
    """

    def __init__(self, sound: "arcade.Sound") -> None:  # type: ignore[name-defined]
        self._sound = sound
        self._player: Optional["pyglet.media.Player"] = None  # type: ignore[name-defined]
        self._loop = True
        self._volume = 0.0

    def play(self, *, loop: bool = True) -> None:
        from pyglet.media import Player  # type: ignore

        self._loop = loop
        # If already playing, ensure loop setting and volume are applied, and return.
        if self._player is not None:
            try:
                self._player.loop = loop
                self._player.volume = self._volume
            except Exception:  # pragma: no cover - defensive
                logger.exception("Failed to set player props during play()")
            return
        try:
            # arcade.Sound.play returns a Player
            self._player = self._sound.play(volume=self._volume, loop=loop)
            # Ensure loop is enforced (some arcade versions don't pass loop)
            self._player.loop = loop
            self._player.volume = self._volume
        except Exception:  # pragma: no cover - cannot run in CI without arcade
            logger.exception("ArcadeTrackPlayer.play failed")
            self._player = None

    def stop(self) -> None:
        if self._player is not None:
            try:
                self._player.pause()
            except Exception:  # pragma: no cover
                logger.exception("ArcadeTrackPlayer.stop failed")
            finally:
                self._player = None

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._player is not None:
            try:
                self._player.volume = self._volume
            except Exception:  # pragma: no cover
                logger.exception("ArcadeTrackPlayer.set_volume failed")

    def get_volume(self) -> float:
        return self._volume

    def is_playing(self) -> bool:
        return self._player is not None


class ArcadeAudioEngine:
    """Factory for ArcadeTrackPlayer using arcade.Sound (optional dependency)."""

    def __init__(self) -> None:
        try:
            import arcade  # noqa: F401
        except Exception as ex:  # pragma: no cover - exercised only when arcade present
            raise RuntimeError(
                "ArcadeAudioEngine requires 'arcade' to be installed"
            ) from ex

    def load_track(self, path: str) -> ArcadeTrackPlayer:  # pragma: no cover
        import arcade

        sound = arcade.Sound(path, streaming=True)
        return ArcadeTrackPlayer(sound)
