from __future__ import annotations

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Combatant:
    """A minimal combatant representation for turn-based combat.

    Attributes:
        name: Display name used in logs.
        max_hp: Maximum hit points (must be >= 1).
        hp: Current hit points (clamped to [0, max_hp]).
        atk: Attack stat (>= 0).
        df: Defense stat (>= 0).
    """

    name: str
    max_hp: int
    hp: int
    atk: int
    df: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Combatant.name must be a non-empty string")
        try:
            self.max_hp = int(self.max_hp)
            self.hp = int(self.hp)
            self.atk = int(self.atk)
            self.df = int(self.df)
        except Exception as exc:
            raise ValueError("Combatant numeric fields must be integers") from exc
        if self.max_hp <= 0:
            raise ValueError("max_hp must be >= 1")
        if self.atk < 0 or self.df < 0:
            logger.warning("Negative atk/df detected for %s; clamping to zero.", self.name)
            self.atk = max(0, self.atk)
            self.df = max(0, self.df)
        # Clamp HP within [0, max_hp]
        if self.hp < 0:
            self.hp = 0
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        """Apply damage to this combatant, clamping HP to zero.

        Args:
            amount: Incoming damage (non-negative).

        Returns:
            The actual damage applied (may be less than amount if HP was low).
        """
        try:
            dmg = int(amount)
        except Exception as exc:
            raise ValueError("damage must be an integer") from exc
        if dmg < 0:
            raise ValueError("damage must be non-negative")

        before = self.hp
        # Death sets HP to 0, strictly.
        self.hp = max(0, self.hp - dmg)
        after = self.hp
        applied = before - after
        return applied
