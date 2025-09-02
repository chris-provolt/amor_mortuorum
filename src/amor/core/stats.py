from __future__ import annotations

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Stats:
    """Basic combat statistics for an entity.

    Attributes:
        hp: Current hit points.
        max_hp: Maximum hit points.
        mp: Current mana points.
        max_mp: Maximum mana points.
        spd: Speed (used for turn order in combat).
        atk: Attack value (placeholder for damage calculation).
        defense: Defense value (placeholder for damage mitigation).
    """

    hp: int
    max_hp: int
    mp: int = 0
    max_mp: int = 0
    spd: int = 10
    atk: int = 5
    defense: int = 5

    def __post_init__(self) -> None:
        # Clamp values to valid ranges
        if self.max_hp <= 0:
            raise ValueError("max_hp must be > 0")
        if self.hp < 0:
            self.hp = 0
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        if self.max_mp < 0:
            raise ValueError("max_mp must be >= 0")
        if self.mp < 0:
            self.mp = 0
        if self.mp > self.max_mp:
            self.mp = self.max_mp
        logger.debug("Stats initialized: %s", self)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        """Apply damage to HP and return actual damage dealt after clamping.

        Args:
            amount: Incoming damage (non-negative).
        """
        if amount < 0:
            raise ValueError("damage cannot be negative")
        original = self.hp
        self.hp = max(0, self.hp - amount)
        dealt = original - self.hp
        logger.debug("Damage taken: requested=%d, dealt=%d, hp=%d", amount, dealt, self.hp)
        return dealt

    def heal(self, amount: int) -> int:
        """Heal HP and return actual healed amount.

        Args:
            amount: Healing amount (non-negative).
        """
        if amount < 0:
            raise ValueError("heal cannot be negative")
        original = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        healed = self.hp - original
        logger.debug("Healed: requested=%d, healed=%d, hp=%d", amount, healed, self.hp)
        return healed

    def spend_mp(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("mp spend cannot be negative")
        original = self.mp
        self.mp = max(0, self.mp - amount)
        spent = original - self.mp
        logger.debug("MP spent: requested=%d, spent=%d, mp=%d", amount, spent, self.mp)
        return spent

    def recover_mp(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("mp recover cannot be negative")
        original = self.mp
        self.mp = min(self.max_mp, self.mp + amount)
        recovered = self.mp - original
        logger.debug("MP recovered: requested=%d, recovered=%d, mp=%d", amount, recovered, self.mp)
        return recovered
