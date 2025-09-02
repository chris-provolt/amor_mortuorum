from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IAudioBackend(ABC):
    """Audio backend interface to decouple game logic from specific libraries (e.g., Arcade).

    Implementations must return an opaque player/handle object from start_music that can be passed
    to stop_music and set_player_volume.
    """

    @abstractmethod
    def start_music(self, path: str, volume: float, loop: bool = True) -> Any:
        """Start playing a music track.

        Args:
            path: File path to the music track
            volume: Initial volume [0..1]
            loop: Should the track loop

        Returns:
            An opaque player handle
        """
        raise NotImplementedError

    @abstractmethod
    def stop_music(self, player: Any) -> None:
        """Stop a music player returned by start_music."""
        raise NotImplementedError

    @abstractmethod
    def set_player_volume(self, player: Any, volume: float) -> None:
        """Set volume [0..1] of a running player."""
        raise NotImplementedError
