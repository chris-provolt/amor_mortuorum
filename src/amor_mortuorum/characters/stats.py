from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class Stats:
    """
    Character stats model with base values and additive equipment modifiers.

    - base_*: intrinsic/base values (no equipment)
    - mod_*: additive modifiers from equipment
    - hp/mp: current resource values
    """

    base_max_hp: int = 100
    base_max_mp: int = 20
    base_atk: int = 5
    base_defense: int = 5
    base_magic: int = 5
    base_resistance: int = 5
    base_speed: int = 5
    base_luck: int = 5

    mod_max_hp: int = 0
    mod_max_mp: int = 0
    mod_atk: int = 0
    mod_defense: int = 0
    mod_magic: int = 0
    mod_resistance: int = 0
    mod_speed: int = 0
    mod_luck: int = 0

    hp: int = field(default=0)
    mp: int = field(default=0)

    def __post_init__(self) -> None:
        # Initialize current values if not set
        if self.hp <= 0:
            self.hp = self.max_hp
        if self.mp <= 0:
            self.mp = self.max_mp

    # Effective properties
    @property
    def max_hp(self) -> int:
        return max(1, self.base_max_hp + self.mod_max_hp)

    @property
    def max_mp(self) -> int:
        return max(0, self.base_max_mp + self.mod_max_mp)

    @property
    def atk(self) -> int:
        return self.base_atk + self.mod_atk

    @property
    def defense(self) -> int:
        return self.base_defense + self.mod_defense

    @property
    def magic(self) -> int:
        return self.base_magic + self.mod_magic

    @property
    def resistance(self) -> int:
        return self.base_resistance + self.mod_resistance

    @property
    def speed(self) -> int:
        return self.base_speed + self.mod_speed

    @property
    def luck(self) -> int:
        return self.base_luck + self.mod_luck

    def _apply_delta(self, key: str, delta: int) -> None:
        if key not in {
            'max_hp', 'max_mp', 'atk', 'defense', 'magic', 'resistance', 'speed', 'luck'
        }:
            logger.debug('Ignoring unsupported stat key: %s', key)
            return
        attr_name = f'mod_{key}' if key in {'max_hp', 'max_mp'} else f'mod_{key}'
        before = getattr(self, attr_name)
        setattr(self, attr_name, before + int(delta))
        logger.debug('Applied delta %s: %d -> %d', attr_name, before, getattr(self, attr_name))
        # Clamp current HP/MP to new maxima
        self._clamp_resources()

    def apply_stat_deltas(self, deltas: Dict[str, int]) -> None:
        """Apply a set of additive stat deltas (e.g., from equipment)."""
        for k, v in deltas.items():
            self._apply_delta(k, int(v))

    def remove_stat_deltas(self, deltas: Dict[str, int]) -> None:
        """Remove a set of additive stat deltas (inverse of apply)."""
        for k, v in deltas.items():
            self._apply_delta(k, -int(v))

    def _clamp_resources(self) -> None:
        old_hp, old_mp = self.hp, self.mp
        self.hp = max(0, min(self.hp, self.max_hp))
        self.mp = max(0, min(self.mp, self.max_mp))
        if (old_hp, old_mp) != (self.hp, self.mp):
            logger.debug('Clamped resources: HP %d->%d MP %d->%d', old_hp, self.hp, old_mp, self.mp)

    def effective_stats(self) -> Dict[str, int]:
        return {
            'max_hp': self.max_hp,
            'max_mp': self.max_mp,
            'atk': self.atk,
            'defense': self.defense,
            'magic': self.magic,
            'resistance': self.resistance,
            'speed': self.speed,
            'luck': self.luck,
        }
