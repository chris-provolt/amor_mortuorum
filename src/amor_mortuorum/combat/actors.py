from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Actor:
    name: str
    max_hp: int
    hp: int

    def is_alive(self) -> bool:
        return self.hp > 0

    def receive_damage(self, amount: int) -> int:
        before = self.hp
        self.hp = max(0, self.hp - max(0, amount))
        return before - self.hp

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, amount))
        return self.hp - before


@dataclass
class Party:
    members: List[Actor] = field(default_factory=list)

    def alive_members(self) -> List[Actor]:
        return [m for m in self.members if m.is_alive()]

    def is_wiped(self) -> bool:
        return all(not m.is_alive() for m in self.members)

    def total_hp(self) -> int:
        return sum(m.hp for m in self.members)
