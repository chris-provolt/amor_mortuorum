from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Actor:
    """
    A combatant within an encounter.

    Attributes:
        name: Display name.
        max_hp: Maximum hit points.
        hp: Current hit points.
        spd: Speed (used for turn order and flee).
        defend_multiplier: If set, the next incoming damage is multiplied by this
            value (e.g., 0.5 to halve the next hit). Cleared immediately after
            the next time damage is taken.
    """

    name: str
    max_hp: int
    spd: int
    hp: int = field(init=False)
    defend_multiplier: Optional[float] = field(default=None)

    def __post_init__(self):
        if self.max_hp <= 0:
            raise ValueError("max_hp must be positive")
        if self.spd < 0:
            raise ValueError("spd must be non-negative")
        self.hp = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def apply_defend(self, multiplier: float) -> None:
        """
        Apply a defend stance that reduces the next damage taken by multiplying it
        with the given multiplier (0 < multiplier <= 1). Typical value is 0.5.

        This status persists until the next time damage is actually taken
        (across turns), then it is automatically cleared.
        """
        if not (0 < multiplier <= 1):
            raise ValueError("Defend multiplier must be within (0, 1].")
        self.defend_multiplier = multiplier
        logger.debug("%s is defending: next damage multiplier set to %.3f", self.name, multiplier)

    def take_damage(self, amount: int) -> int:
        """
        Apply incoming damage to this actor.

        If a defend multiplier is active, it is applied to the damage of this
        event, with results floored (but at least 1 damage if incoming damage > 0).
        The defend multiplier is then cleared (one-time effect).

        Returns the actual damage applied.
        """
        if amount < 0:
            raise ValueError("Damage amount cannot be negative.")
        if not self.alive:
            logger.debug("%s is already down. Incoming damage ignored.", self.name)
            return 0

        original = amount
        if self.defend_multiplier is not None and amount > 0:
            amount = max(1, math.floor(amount * self.defend_multiplier))
            logger.debug(
                "%s had defend active (%.3f): %d -> %d",
                self.name,
                self.defend_multiplier,
                original,
                amount,
            )
            # Clear defend after use
            self.defend_multiplier = None

        self.hp = max(0, self.hp - amount)
        logger.debug("%s takes %d damage (HP: %d/%d)", self.name, amount, self.hp, self.max_hp)
        return amount

    def heal(self, amount: int) -> int:
        """Heal this actor by amount, not exceeding max HP. Returns actual healed amount."""
        if amount < 0:
            raise ValueError("Heal amount cannot be negative.")
        if not self.alive:
            return 0
        prev = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        healed = self.hp - prev
        if healed:
            logger.debug("%s heals %d HP (HP: %d/%d)", self.name, healed, self.hp, self.max_hp)
        return healed


@dataclass
class Party:
    """
    A group of actors. Used for both player party and enemy group.
    """

    name: str
    members: List[Actor]

    def alive_members(self) -> List[Actor]:
        return [m for m in self.members if m.alive]

    def is_wiped(self) -> bool:
        return len(self.alive_members()) == 0

    def average_spd(self) -> float:
        alive = self.alive_members()
        if not alive:
            return 0.0
        return sum(m.spd for m in alive) / len(alive)

    def sum_spd(self) -> int:
        return sum(m.spd for m in self.alive_members())

    def aggregate_spd(self, method: str = "average") -> float:
        """
        Aggregate speed according to method: 'average' (default) or 'sum'.
        """
        method = method.lower()
        if method == "average":
            return self.average_spd()
        if method == "sum":
            return float(self.sum_spd())
        raise ValueError(f"Unsupported SPD aggregation method: {method}")

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Party(name={self.name!r}, members={[m.name for m in self.members]!r})"
