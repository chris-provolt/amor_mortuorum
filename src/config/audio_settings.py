from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioSettings:
    """Runtime audio settings.

    Volumes are linear multipliers in the range [0.0, 1.0].
    Only master and music are used for ambient tracks.
    """

    master_volume: float = 1.0
    music_volume: float = 1.0
    sfx_volume: float = 1.0

    def __post_init__(self) -> None:
        self.master_volume = self._clamp(self.master_volume)
        self.music_volume = self._clamp(self.music_volume)
        self.sfx_volume = self._clamp(self.sfx_volume)

    @staticmethod
    def _clamp(v: float) -> float:
        try:
            if v is None:
                return 1.0
            return max(0.0, min(1.0, float(v)))
        except Exception:
            return 1.0

    @property
    def effective_music_volume(self) -> float:
        """Compute the effective music volume (master * music)."""
        return float(self.master_volume) * float(self.music_volume)

    def update(self, *, master_volume: Optional[float] = None, music_volume: Optional[float] = None, sfx_volume: Optional[float] = None) -> None:
        if master_volume is not None:
            self.master_volume = self._clamp(master_volume)
        if music_volume is not None:
            self.music_volume = self._clamp(music_volume)
        if sfx_volume is not None:
            self.sfx_volume = self._clamp(sfx_volume)
