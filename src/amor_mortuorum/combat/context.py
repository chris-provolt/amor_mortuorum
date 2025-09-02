from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from amor_mortuorum.inventory.inventory import Inventory
from amor_mortuorum.utils.math import clamp


@dataclass
class Combatant:
    """
    Simple combatant model with HP/MP and an inventory.
    """

    name: str
    hp: int
    hp_max: int
    mp: int
    mp_max: int
    inventory: Inventory = field(default_factory=Inventory)

    def __post_init__(self) -> None:
        # Sanitize initial values
        self.hp = clamp(self.hp, 0, self.hp_max)
        self.mp = clamp(self.mp, 0, self.mp_max)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def heal_hp(self, amount: int) -> int:
        if amount <= 0:
            return 0
        new_hp = clamp(self.hp + amount, 0, self.hp_max)
        healed = new_hp - self.hp
        self.hp = new_hp
        return healed

    def restore_mp(self, amount: int) -> int:
        if amount <= 0:
            return 0
        new_mp = clamp(self.mp + amount, 0, self.mp_max)
        restored = new_mp - self.mp
        self.mp = new_mp
        return restored

    def take_damage(self, amount: int) -> int:
        if amount <= 0:
            return 0
        new_hp = clamp(self.hp - amount, 0, self.hp_max)
        dealt = self.hp - new_hp
        self.hp = new_hp
        return dealt


@dataclass
class CombatContext:
    """
    Minimal combat context to support item usage.

    Holds two teams of combatants and a simple text log of events.
    """

    team_a: List[Combatant]
    team_b: List[Combatant]
    log: List[str] = field(default_factory=list)

    def allies_of(self, actor: Combatant) -> Sequence[Combatant]:
        if actor in self.team_a:
            return tuple(self.team_a)
        elif actor in self.team_b:
            return tuple(self.team_b)
        raise ValueError("Actor is not in this combat context.")

    def enemies_of(self, actor: Combatant) -> Sequence[Combatant]:
        if actor in self.team_a:
            return tuple(self.team_b)
        elif actor in self.team_b:
            return tuple(self.team_a)
        raise ValueError("Actor is not in this combat context.")

    def add_log(self, entry: str) -> None:
        self.log.append(entry)
