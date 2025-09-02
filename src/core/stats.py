from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatBlock:
    """Immutable block of core/derived stats.

    All values are non-negative integers and represent maximums or derived totals.
    These values are designed to be additive between base stats and equipment bonuses.
    """

    max_hp: int = 0
    max_mp: int = 0
    attack: int = 0
    defense: int = 0
    magic: int = 0
    speed: int = 0

    def __post_init__(self) -> None:
        # Validate non-negative integers
        for field_name, value in self.__dict__.items():
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be an int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative, got {value}")

    def __add__(self, other: "StatBlock") -> "StatBlock":
        if not isinstance(other, StatBlock):
            return NotImplemented
        return StatBlock(
            max_hp=self.max_hp + other.max_hp,
            max_mp=self.max_mp + other.max_mp,
            attack=self.attack + other.attack,
            defense=self.defense + other.defense,
            magic=self.magic + other.magic,
            speed=self.speed + other.speed,
        )

    def __sub__(self, other: "StatBlock") -> "StatBlock":
        if not isinstance(other, StatBlock):
            return NotImplemented
        # Clamp at 0 to avoid negative stats
        return StatBlock(
            max_hp=max(0, self.max_hp - other.max_hp),
            max_mp=max(0, self.max_mp - other.max_mp),
            attack=max(0, self.attack - other.attack),
            defense=max(0, self.defense - other.defense),
            magic=max(0, self.magic - other.magic),
            speed=max(0, self.speed - other.speed),
        )

    @staticmethod
    def zeros() -> "StatBlock":
        return StatBlock()

    def to_dict(self) -> dict:
        return {
            "max_hp": self.max_hp,
            "max_mp": self.max_mp,
            "attack": self.attack,
            "defense": self.defense,
            "magic": self.magic,
            "speed": self.speed,
        }
