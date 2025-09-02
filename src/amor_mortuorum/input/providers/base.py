from __future__ import annotations

import abc
from typing import Iterable, List

from ..actions import InputEvent


class InputProvider(abc.ABC):
    """Abstract base class for an input provider backend.

    Implementations feed InputEvents to the game loop (e.g., by polling or by
    consuming window-system callbacks). They should be thin adapters that
    translate raw device input into InputEvents via an InputMapper.
    """

    @abc.abstractmethod
    def update(self) -> None:
        """Poll/refresh the underlying input backend if necessary."""

    @abc.abstractmethod
    def get_events(self) -> List[InputEvent]:
        """Return and clear any queued input events since the last call."""


__all__ = ["InputProvider"]
