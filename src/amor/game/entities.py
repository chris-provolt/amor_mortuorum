from dataclasses import dataclass
from typing import Tuple


@dataclass
class Entity:
    """Base entity in the world grid."""
    eid: str
    name: str
    x: int
    y: int

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def move_to(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class Actor(Entity):
    """An actor with health that can take damage."""

    def __init__(self, eid: str, name: str, x: int, y: int, max_hp: int) -> None:
        super().__init__(eid=eid, name=name, x=x, y=y)
        if max_hp <= 0:
            raise ValueError("max_hp must be positive")
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def __repr__(self) -> str:
        return f"Actor({self.name}@{self.x},{self.y} hp={self.hp}/{self.max_hp})"
