from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .xp_curve import XPCurve

logger = logging.getLogger(__name__)


@dataclass
class Stats:
    """Core character stats.

    This includes max values for HP/MP and primary attributes.
    """

    max_hp: int
    max_mp: int
    atk: int
    defense: int
    magic: int
    resistance: int
    speed: int
    luck: int

    def apply_delta(self, delta: "StatsDelta") -> None:
        self.max_hp += delta.max_hp
        self.max_mp += delta.max_mp
        self.atk += delta.atk
        self.defense += delta.defense
        self.magic += delta.magic
        self.resistance += delta.resistance
        self.speed += delta.speed
        self.luck += delta.luck


@dataclass
class StatsDelta:
    max_hp: int = 0
    max_mp: int = 0
    atk: int = 0
    defense: int = 0
    magic: int = 0
    resistance: int = 0
    speed: int = 0
    luck: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "max_hp": self.max_hp,
            "max_mp": self.max_mp,
            "atk": self.atk,
            "defense": self.defense,
            "magic": self.magic,
            "resistance": self.resistance,
            "speed": self.speed,
            "luck": self.luck,
        }


@dataclass
class Character:
    """Minimal character model for leveling purposes.

    This class is intentionally light so it can be adapted to the project's
    actual entity system. It includes only what's necessary for progression.
    """

    name: str
    level: int = 1
    total_xp: int = 0
    stats: Stats = field(default_factory=lambda: Stats(30, 10, 5, 5, 3, 3, 4, 1))
    alive: bool = True  # For XP distribution in battle rewards


@dataclass
class LevelUpEvent:
    from_level: int
    to_level: int
    delta: StatsDelta


@dataclass
class LevelUpResult:
    levels_gained: int
    events: List[LevelUpEvent]
    remaining_xp_to_next: Optional[int]


@dataclass
class GrowthConfig:
    """Deterministic stat growth configuration.

    The default config yields steady growth with small periodic bonuses.
    """

    # HP/MP base per-level growth functions depend on current level L before leveling
    def hp_increase(self, L: int) -> int:
        return 10 + (L // 2)

    def mp_increase(self, L: int) -> int:
        return 3 + (L // 3)

    # Primary stats: base + periodic bonuses
    def atk_increase(self, L: int) -> int:
        return 2 + (1 if (L + 1) % 5 == 0 else 0)

    def defense_increase(self, L: int) -> int:
        return 2 + (1 if (L + 1) % 5 == 0 else 0)

    def magic_increase(self, L: int) -> int:
        return 2 + (1 if (L + 1) % 5 == 0 else 0)

    def resistance_increase(self, L: int) -> int:
        return 2 + (1 if (L + 1) % 5 == 0 else 0)

    def speed_increase(self, L: int) -> int:
        return 1 + (1 if (L + 1) % 3 == 0 else 0)

    def luck_increase(self, L: int) -> int:
        return 1 if (L + 1) % 2 == 0 else 0


class LevelingSystem:
    """Handles XP accrual and stat growth for characters.

    - Uses an XPCurve for XP thresholds.
    - Applies deterministic stat growth on each level-up.
    """

    def __init__(self, xp_curve: XPCurve, growth: Optional[GrowthConfig] = None) -> None:
        self.xp_curve = xp_curve
        self.growth = growth or GrowthConfig()

    def xp_to_next(self, character: Character) -> Optional[int]:
        if character.level >= self.xp_curve.max_level:
            return None
        current_total_needed = self.xp_curve.total_xp_for_level(character.level + 1)
        return max(0, current_total_needed - character.total_xp)

    def add_xp(self, character: Character, amount: int) -> LevelUpResult:
        if amount < 0:
            raise ValueError("XP amount cannot be negative")
        start_level = character.level
        character.total_xp += amount
        events: List[LevelUpEvent] = []

        # Level up while XP exceeds next threshold and not at cap
        while character.level < self.xp_curve.max_level:
            next_threshold = self.xp_curve.total_xp_for_level(character.level + 1)
            if character.total_xp >= next_threshold:
                delta = self._compute_level_up_delta(character.level)
                from_level = character.level
                character.level += 1
                character.stats.apply_delta(delta)
                events.append(LevelUpEvent(from_level=from_level, to_level=character.level, delta=delta))
                logger.debug(
                    "Level up: %s from L%d to L%d, delta=%s", character.name, from_level, character.level, delta.as_dict()
                )
            else:
                break

        remaining = self.xp_to_next(character)
        result = LevelUpResult(levels_gained=character.level - start_level, events=events, remaining_xp_to_next=remaining)
        return result

    def _compute_level_up_delta(self, current_level: int) -> StatsDelta:
        g = self.growth
        delta = StatsDelta(
            max_hp=g.hp_increase(current_level),
            max_mp=g.mp_increase(current_level),
            atk=g.atk_increase(current_level),
            defense=g.defense_increase(current_level),
            magic=g.magic_increase(current_level),
            resistance=g.resistance_increase(current_level),
            speed=g.speed_increase(current_level),
            luck=g.luck_increase(current_level),
        )
        return delta
