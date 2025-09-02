from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AudioManager(ABC):
    """Abstract audio manager interface for playing sound cues.

    The game's main audio subsystem should implement this interface. For tests
    and environments without audio support, use NullAudioManager or a fake.
    """

    @abstractmethod
    def has_cue(self, cue: str) -> bool:  # pragma: no cover - interface
        """Return True if a given cue/sound name is available to play."""

    @abstractmethod
    def play(self, cue: str) -> None:  # pragma: no cover - interface
        """Play a sound cue by name."""


class NullAudioManager(AudioManager):
    """No-op audio manager that never plays sounds.

    Useful as a safe default in headless/test environments.
    """

    def has_cue(self, cue: str) -> bool:
        return False

    def play(self, cue: str) -> None:
        logger.debug("NullAudioManager.play called with cue '%s' (no-op)", cue)
