from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .inventory import Inventory


@dataclass
class Player:
    """Player entity representation minimal for this feature.

    The Player delegates death handling to the GameState to allow game-wide
    transitions (e.g. location changes) and effects.
    """

    name: str
    max_hp: int
    hp: int
    inventory: Inventory

    def is_alive(self) -> bool:
        return self.hp > 0

    def heal_to(self, hp_value: int) -> None:
        self.hp = max(0, min(self.max_hp, hp_value))

    def take_damage(self, amount: int, game_state: "GameState") -> None:
        """Apply damage; if HP <= 0, ask game_state to handle death logic."""
        if amount < 0:
            raise ValueError("Damage amount must be non-negative")
        if self.hp <= 0:
            return  # already dead; ignore further damage
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            game_state.handle_player_death(self)


# Avoid circular import at type-check time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from amormortuorum.game.game_state import GameState
