from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
import math


class CombatLog:
    """Simple combat log to capture events and distinct telegraphs for UI."""

    def __init__(self) -> None:
        self.events: List[str] = []
        self.telegraphs: List[Tuple[str, str]] = []  # (entity_name, message)

    def add(self, msg: str) -> None:
        self.events.append(msg)

    def telegraph(self, who: str, msg: str) -> None:
        self.telegraphs.append((who, msg))
        # Also log as event for completeness
        self.add(f"{who} telegraphs: {msg}")


@dataclass
class Stats:
    max_hp: int
    hp: int
    atk: int
    defense: int
    spd: int

    def take_damage(self, amount: int) -> int:
        amount = max(0, int(amount))
        old = self.hp
        self.hp = max(0, self.hp - amount)
        return old - self.hp

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class DamageEvent:
    source: "Entity"
    target: "Entity"
    amount: int
    damage_type: str = "physical"
    is_reflected: bool = False


class Action:
    pass


@dataclass
class AttackAction(Action):
    attacker: "Entity"
    target: "Entity"


@dataclass
class SummonAction(Action):
    summoner: "Entity"
    count: int = 2


@dataclass
class CastReflectAction(Action):
    caster: "Entity"
    duration: int
    ratio: float


@dataclass
class NoopAction(Action):
    actor: "Entity"


class Status:
    """Base Status class with optional duration and hooks around damage."""

    name: str = "Status"
    duration: Optional[int] = None  # turns; None = infinite

    def __init__(self, duration: Optional[int] = None) -> None:
        self.duration = duration

    def on_apply(self, entity: "Entity", ctx: "BattleContext") -> None:
        pass

    def on_remove(self, entity: "Entity", ctx: "BattleContext") -> None:
        pass

    def on_pre_receive_damage(self, entity: "Entity", dmg: DamageEvent, ctx: "BattleContext") -> None:
        pass

    def on_post_receive_damage(self, entity: "Entity", dealt: int, dmg: DamageEvent, ctx: "BattleContext") -> List[DamageEvent]:
        return []

    def tick(self, entity: "Entity", ctx: "BattleContext") -> None:
        if self.duration is not None:
            self.duration -= 1

    def expired(self) -> bool:
        return self.duration is not None and self.duration <= 0


class ShieldStatus(Status):
    name = "Shield"

    def __init__(self, points: int) -> None:
        super().__init__(duration=None)
        self.points = int(points)

    def on_pre_receive_damage(self, entity: "Entity", dmg: DamageEvent, ctx: "BattleContext") -> None:
        if self.points <= 0:
            return
        absorbed = min(self.points, dmg.amount)
        self.points -= absorbed
        dmg.amount -= absorbed
        ctx.log.add(f"{entity.name}'s shield absorbs {absorbed} damage (remaining {self.points}).")

    def expired(self) -> bool:
        return self.points <= 0


class ReflectStatus(Status):
    name = "Reflect"

    def __init__(self, ratio: float, duration: int) -> None:
        super().__init__(duration=duration)
        self.ratio = float(ratio)

    def on_post_receive_damage(self, entity: "Entity", dealt: int, dmg: DamageEvent, ctx: "BattleContext") -> List[DamageEvent]:
        if dealt <= 0:
            return []
        reflected = int(math.floor(dealt * self.ratio))
        if reflected <= 0:
            return []
        source = dmg.source
        if not source.alive:
            return []
        ctx.log.add(f"{entity.name}'s Mirror Veil reflects {reflected} damage back to {source.name}!")
        return [DamageEvent(source=entity, target=source, amount=reflected, damage_type=dmg.damage_type, is_reflected=True)]


class EnrageStatus(Status):
    name = "Enrage"

    def __init__(self, atk_multiplier: float = 1.5) -> None:
        super().__init__(duration=None)
        self.atk_multiplier = float(atk_multiplier)


class BattleContext:
    def __init__(self, engine: "BattleEngine", log: CombatLog) -> None:
        self.engine = engine
        self.log = log


class Entity:
    def __init__(self, name: str, team: str, stats: Stats, is_player: bool = False) -> None:
        self.name = name
        self.team = team
        self.stats = stats
        self.statuses: List[Status] = []
        self.is_player = is_player
        self.temp_atk_mult: float = 1.0
        self.controller: Optional["Controller"] = None

    @property
    def alive(self) -> bool:
        return self.stats.alive

    def add_status(self, status: Status, ctx: BattleContext) -> None:
        self.statuses.append(status)
        status.on_apply(self, ctx)

    def remove_expired_statuses(self, ctx: BattleContext) -> None:
        new_statuses: List[Status] = []
        for s in self.statuses:
            if s.expired():
                s.on_remove(self, ctx)
                ctx.log.add(f"{self.name}'s {s.name} wears off.")
            else:
                new_statuses.append(s)
        self.statuses = new_statuses

    def tick_statuses(self, ctx: BattleContext) -> None:
        for s in self.statuses:
            s.tick(self, ctx)

    def pre_receive_damage(self, dmg: DamageEvent, ctx: BattleContext) -> None:
        for s in list(self.statuses):
            s.on_pre_receive_damage(self, dmg, ctx)

    def post_receive_damage(self, dealt: int, dmg: DamageEvent, ctx: BattleContext) -> List[DamageEvent]:
        extra: List[DamageEvent] = []
        for s in list(self.statuses):
            extra.extend(s.on_post_receive_damage(self, dealt, dmg, ctx))
        return extra

    def receive_damage(self, dmg: DamageEvent, ctx: BattleContext) -> int:
        if not self.alive:
            return 0
        self.pre_receive_damage(dmg, ctx)
        dealt = self.stats.take_damage(dmg.amount)
        ctx.log.add(f"{dmg.source.name} deals {dealt} to {self.name}.")
        extra = self.post_receive_damage(dealt, dmg, ctx)
        for ed in extra:
            # prevent reflect-of-reflect loops
            if ed.is_reflected:
                ed.is_reflected = False
            self._apply_extra_damage(ed, ctx)
        return dealt

    def _apply_extra_damage(self, dmg: DamageEvent, ctx: BattleContext) -> None:
        if dmg.target.alive:
            dmg.target.receive_damage(dmg, ctx)

    def compute_attack_damage(self, target: "Entity") -> int:
        base_atk = int(round(self.stats.atk * self.effective_atk_multiplier()))
        dmg = max(1, base_atk - target.stats.defense)
        return dmg

    def effective_atk_multiplier(self) -> float:
        mult = self.temp_atk_mult
        for s in self.statuses:
            if isinstance(s, EnrageStatus):
                mult *= s.atk_multiplier
        return mult

    def choose_action(self, ctx: BattleContext) -> Action:
        # Default AI: Attack first living enemy
        target = ctx.engine.first_living_opponent(self)
        if target is None:
            return NoopAction(actor=self)
        return AttackAction(attacker=self, target=target)


class Controller:
    """Optional controller for specialized behaviors (bosses)."""

    def on_battle_start(self, entity: Entity, ctx: BattleContext) -> None:
        pass

    def on_turn_start(self, entity: Entity, ctx: BattleContext) -> None:
        pass

    def on_turn_end(self, entity: Entity, ctx: BattleContext) -> None:
        pass

    def on_receive_damage(self, entity: Entity, dmg: DamageEvent, ctx: BattleContext) -> None:
        pass

    def choose_action(self, entity: Entity, ctx: BattleContext) -> Action:
        return entity.choose_action(ctx)


