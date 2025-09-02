from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .actors import Actor, Party


class Action:
    name: str

    def execute(self, boss: "BaseBoss", party: Party) -> Dict:
        raise NotImplementedError


@dataclass
class DamageAction(Action):
    name: str
    damage: int
    target: str  # 'single' or 'all'

    def execute(self, boss: "BaseBoss", party: Party) -> Dict:
        result: Dict = {"name": self.name, "type": "damage", "target": self.target, "applied": []}
        if self.target == "all":
            for m in party.alive_members():
                dealt = m.receive_damage(self.damage)
                result["applied"].append({"to": m.name, "damage": dealt})
        else:  # single target: choose the actor with highest HP among alive
            alive = party.alive_members()
            if alive:
                target = max(alive, key=lambda a: a.hp)
                dealt = target.receive_damage(self.damage)
                result["applied"].append({"to": target.name, "damage": dealt})
        return result


@dataclass
class DrainAction(Action):
    name: str
    damage: int
    heal_ratio: float  # 0..1

    def execute(self, boss: "BaseBoss", party: Party) -> Dict:
        result: Dict = {"name": self.name, "type": "drain", "applied": []}
        alive = party.alive_members()
        if alive:
            target = max(alive, key=lambda a: a.hp)
            dealt = target.receive_damage(self.damage)
            healed = boss.heal(int(dealt * self.heal_ratio))
            result["applied"].append({"to": target.name, "damage": dealt, "healed": healed})
        return result


@dataclass
class HealSelfPercent(Action):
    name: str
    percent: float  # 0..1

    def execute(self, boss: "BaseBoss", party: Party) -> Dict:
        amount = int(boss.max_hp * self.percent)
        healed = boss.heal(amount)
        return {"name": self.name, "type": "heal", "healed": healed}


@dataclass
class MultiAction(Action):
    name: str
    actions: List[Action]

    def execute(self, boss: "BaseBoss", party: Party) -> Dict:
        results: List[Dict] = []
        for act in self.actions:
            results.append(act.execute(boss, party))
        return {"name": self.name, "type": "multi", "steps": results}
