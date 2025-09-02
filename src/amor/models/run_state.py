from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Character:
    """Minimal character representation for snapshotting.

    Extend as needed; keep to primitives or nested dataclasses with to_dict.
    """

    name: str
    level: int
    hp: int
    max_hp: int

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Character name cannot be empty")
        if self.level < 1:
            raise ValueError("Character level must be >= 1")
        if self.max_hp <= 0:
            raise ValueError("Character max_hp must be > 0")
        if not (0 <= self.hp <= self.max_hp):
            raise ValueError("Character hp must be within [0, max_hp]")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Character":
        c = Character(
            name=str(data["name"]),
            level=int(data["level"]),
            hp=int(data["hp"]),
            max_hp=int(data["max_hp"]),
        )
        c.validate()
        return c


@dataclass
class Party:
    """Party container for snapshotting mid-run."""

    members: List[Character] = field(default_factory=list)

    def validate(self) -> None:
        if len(self.members) == 0:
            raise ValueError("Party must have at least 1 member")
        for m in self.members:
            m.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {"members": [m.to_dict() for m in self.members]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Party":
        members = [Character.from_dict(m) for m in data.get("members", [])]
        p = Party(members=members)
        p.validate()
        return p


@dataclass
class RunState:
    """Minimal run state for volatile snapshot save-and-quit.

    This is not the full persistent save; it is a volatile snapshot consumed on load.
    Acceptance criteria requires: restores party, floor, seed.
    """

    floor: int
    dungeon_seed: int
    party: Party
    # Additional fields can be added as needed, e.g., inventory, timers, etc.

    def validate(self) -> None:
        if not isinstance(self.floor, int) or self.floor < 1:
            raise ValueError("floor must be >= 1")
        if not isinstance(self.dungeon_seed, int):
            raise ValueError("dungeon_seed must be an int")
        self.party.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "floor": self.floor,
            "dungeon_seed": self.dungeon_seed,
            "party": self.party.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RunState":
        rs = RunState(
            floor=int(data["floor"]),
            dungeon_seed=int(data["dungeon_seed"]),
            party=Party.from_dict(data["party"]),
        )
        rs.validate()
        return rs

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @staticmethod
    def from_json(s: str) -> "RunState":
        return RunState.from_dict(json.loads(s))
