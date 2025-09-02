from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MovementEvent:
    """Event emitted when the player enters a new tile.

    Attributes:
        position: integer tile coordinates after the move.
        steps_taken: counter since some origin (optional semantics managed by scene).
    """

    position: Tuple[int, int]
    steps_taken: int


@dataclass(frozen=True)
class EnterCombatEvent:
    """Event indicating that a random encounter has triggered."""

    source_position: Tuple[int, int]
    floor: int
