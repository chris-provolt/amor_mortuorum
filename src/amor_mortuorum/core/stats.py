from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Optional

logger = logging.getLogger(__name__)


class Stat(Enum):
    """
    Primary character stats used across the game. This is intentionally small for
    early implementation but can be expanded as the game grows.
    """

    HP = "HP"         # Max hit points (preview reflects max stat, not current)
    ATK = "ATK"       # Physical attack
    DEF = "DEF"       # Physical defense
    MAG = "MAG"       # Magic power
    RES = "RES"       # Magic resistance
    SPD = "SPD"       # Speed (turn order)
    LUCK = "LUCK"     # Luck (crits, drops, etc.)


@dataclass
class CharacterStats:
    """
    Immutable-style container for character stats with convenience arithmetic.

    Internally maintains values for all Stat keys. Missing stats default to 0.
    """

    values: Dict[Stat, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Ensure all Stats exist in mapping; default to 0
        self.values = {stat: int(self.values.get(stat, 0)) for stat in Stat}

    @classmethod
    def from_dict(cls, raw: Dict[str, int]) -> "CharacterStats":
        return cls({Stat(k): int(v) for k, v in raw.items()})

    def to_dict(self) -> Dict[str, int]:
        return {stat.value: val for stat, val in self.values.items()}

    def copy(self) -> "CharacterStats":
        return CharacterStats(dict(self.values))

    def plus(self, other: "CharacterStats") -> "CharacterStats":
        return CharacterStats({s: self.values.get(s, 0) + other.values.get(s, 0) for s in Stat})

    def minus(self, other: "CharacterStats") -> "CharacterStats":
        return CharacterStats({s: self.values.get(s, 0) - other.values.get(s, 0) for s in Stat})

    def add_inplace(self, other: "CharacterStats") -> None:
        for s in Stat:
            self.values[s] = self.values.get(s, 0) + other.values.get(s, 0)

    def is_zero(self) -> bool:
        return all(v == 0 for v in self.values.values())

    @staticmethod
    def sum(stats: Iterable["CharacterStats"]) -> "CharacterStats":
        total: Dict[Stat, int] = {s: 0 for s in Stat}
        for st in stats:
            for s in Stat:
                total[s] += st.values.get(s, 0)
        return CharacterStats(total)

    def non_zero_items(self) -> Dict[Stat, int]:
        return {s: v for s, v in self.values.items() if v != 0}

    def __getitem__(self, stat: Stat) -> int:
        return self.values.get(stat, 0)

    def __repr__(self) -> str:
        inner = ", ".join(f"{s.value}={v}" for s, v in self.values.items())
        return f"CharacterStats({inner})"
