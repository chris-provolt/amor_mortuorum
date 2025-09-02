from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import logging

try:
    import arcade
except Exception:  # pragma: no cover - Import errors handled at runtime where used
    arcade = None  # type: ignore

from ..interfaces import IAudioBackend

logger = logging.getLogger(__name__)


@dataclass
class _ArcadeMusicPlayer:
    sound: Any
    player: Any


class ArcadeAudioBackend(IAudioBackend):
    """Arcade-based audio backend for ambient music.

    Uses arcade.Sound(..., streaming=True) for long tracks and returns a wrapper
    with both sound and player to allow proper stop and volume control.
    """

    def __init__(self) -> None:
        if arcade is None:  # pragma: no cover - runtime guard
            raise RuntimeError("arcade is not available. Install 'arcade' to use ArcadeAudioBackend.")

    def start_music(self, path: str, volume: float, loop: bool = True) -> _ArcadeMusicPlayer:
        if not isinstance(path, str) or not path:
            raise ValueError("Invalid music path")
        # arcade.Sound with streaming=True is recommended for music/long files
        sound = arcade.Sound(path, streaming=True)
        # arcade 2.x: .play returns a pyglet.media.Player
        player = sound.play(volume=volume, looping=loop)
        logger.debug("Arcade start_music: path=%s vol=%.3f loop=%s", path, volume, loop)
        return _ArcadeMusicPlayer(sound=sound, player=player)

    def stop_music(self, player: _ArcadeMusicPlayer) -> None:
        if not isinstance(player, _ArcadeMusicPlayer):
            return
        try:
            # Pyglet Player supports pause() to stop playback
            if getattr(player, "player", None) is not None:
                player.player.pause()
        finally:
            # Explicitly delete references to help GC
            player.player = None  # type: ignore
            player.sound = None  # type: ignore
        logger.debug("Arcade stop_music called")

    def set_player_volume(self, player: _ArcadeMusicPlayer, volume: float) -> None:
        if not isinstance(player, _ArcadeMusicPlayer):
            return
        v = max(0.0, min(1.0, float(volume)))
        if getattr(player, "player", None) is not None:
            player.player.volume = v
        logger.debug("Arcade set_player_volume: %.3f", v)
