from __future__ import annotations

from typing import Optional

from ..combat.core import (
    Action,
    AttackAction,
    CastReflectAction,
    DamageEvent,
    EnrageStatus,
    Entity,
    NoopAction,
    ReflectStatus,
    Stats,
    SummonAction,
)
from .miniboss_base import BaseMiniboss


class ShieldedMiniboss(BaseMiniboss):
    """Miniboss with a protective shield that must be broken first.

    Mechanic: Starts battle with a sizeable Shield that absorbs incoming damage.
    Telegraph: "An Aegis shimmers around ..."
    """

    name = "Shielded Miniboss"

    def __init__(self, shield_points: Optional[int] = None) -> None:
        self.shield_points = shield_points

    def on_battle_start(self, entity: Entity, ctx) -> None:
        amount = self.shield_points
        if amount is None:
            # default: 30% of max HP rounded up
            amount = int(round(entity.stats.max_hp * 0.3))
        self.give_opening_shield(entity, ctx, amount, "An Aegis shimmers into being!")

    def choose_action(self, entity: Entity, ctx) -> Action:
        target = ctx.engine.first_living_opponent(entity)
        if not target:
            return NoopAction(actor=entity)
        return AttackAction(attacker=entity, target=target)


class SummonerMiniboss(BaseMiniboss):
    """Miniboss that periodically summons adds.

    Mechanic: Every N turns, telegraphs a chant, then summons allies next turn.
    Telegraph: "Chanting to summon allies..."
    """

    name = "Summoner Miniboss"

    def __init__(self, cadence: int = 3, adds: int = 2) -> None:
        self.cadence = max(2, cadence)  # at least 2 to have a telegraph turn
        self.adds = max(1, adds)
        self.turns_until_summon = self.cadence  # starts counting down
        self._telegraphed = False

    def on_turn_start(self, entity: Entity, ctx) -> None:
        # if about to summon (after telegraph), do nothing special here
        pass

    def on_turn_end(self, entity: Entity, ctx) -> None:
        self.turns_until_summon -= 1
        if self.turns_until_summon == 1 and not self._telegraphed:
            self.telegraph(entity, "Chanting to summon allies...", ctx)
            self._telegraphed = True
        if self.turns_until_summon <= 0:
            # reset for the next cycle after action executes
            self.turns_until_summon = self.cadence
            self._telegraphed = False

    def choose_action(self, entity: Entity, ctx) -> Action:
        # if the last on_turn_end set the counter to cadence (meaning summon now)
        # we summon at the start of this turn when _telegraphed was set last turn
        if self._telegraphed and self.turns_until_summon == self.cadence:
            return SummonAction(summoner=entity, count=self.adds)
        # else attack
        target = ctx.engine.first_living_opponent(entity)
        if not target:
            return NoopAction(actor=entity)
        return AttackAction(attacker=entity, target=target)


class EnragedMiniboss(BaseMiniboss):
    """Miniboss that enrages at low HP, increasing damage output.

    Mechanic: On first dropping below threshold HP, gains Enrage increasing ATK.
    Telegraph: "Blood fury!"
    """

    name = "Enraged Miniboss"

    def __init__(self, threshold: float = 0.5, atk_multiplier: float = 1.5) -> None:
        self.threshold = float(threshold)
        self.atk_multiplier = float(atk_multiplier)
        self._enraged = False

    def on_receive_damage(self, entity: Entity, dmg: DamageEvent, ctx) -> None:
        # Hook before damage is applied not reliable for threshold; use turn start check
        pass

    def on_turn_start(self, entity: Entity, ctx) -> None:
        if not self._enraged and entity.stats.hp <= int(entity.stats.max_hp * self.threshold):
            self._enraged = True
            entity.add_status(EnrageStatus(atk_multiplier=self.atk_multiplier), ctx)
            self.telegraph(entity, "Blood fury courses through veins!", ctx)

    def choose_action(self, entity: Entity, ctx) -> Action:
        target = ctx.engine.first_living_opponent(entity)
        if not target:
            return NoopAction(actor=entity)
        return AttackAction(attacker=entity, target=target)


class ReflectMiniboss(BaseMiniboss):
    """Miniboss that periodically gains a reflect buff.

    Mechanic: Applies Mirror Veil that reflects a portion of damage for M turns.
    Telegraph: "The Mirror Veil shimmers..."
    """

    name = "Reflect Miniboss"

    def __init__(self, cooldown: int = 3, duration: int = 2, ratio: float = 0.5) -> None:
        self.cooldown = max(1, cooldown)
        self.duration = max(1, duration)
        self.ratio = float(ratio)
        self._cool = 0  # cast immediately on first turn

    def on_turn_start(self, entity: Entity, ctx) -> None:
        # If reflect not present and cooldown elapsed, cast this turn
        has_reflect = any(isinstance(s, ReflectStatus) for s in entity.statuses)
        if not has_reflect and self._cool <= 0:
            # Telegraph right before gaining reflect
            self.telegraph(entity, "The Mirror Veil shimmers into place...", ctx)

    def choose_action(self, entity: Entity, ctx) -> Action:
        has_reflect = any(isinstance(s, ReflectStatus) for s in entity.statuses)
        if not has_reflect and self._cool <= 0:
            # Cast reflect now
            self._cool = self.cooldown
            return CastReflectAction(caster=entity, duration=self.duration, ratio=self.ratio)
        # Otherwise attack
        target = ctx.engine.first_living_opponent(entity)
        if not target:
            return NoopAction(actor=entity)
        return AttackAction(attacker=entity, target=target)

    def on_turn_end(self, entity: Entity, ctx) -> None:
        self._cool -= 1


# Factory helpers to build miniboss entities ready for battle

def make_miniboss_shielded(name: str = "Aegis Warden") -> Entity:
    stats = Stats(max_hp=120, hp=120, atk=15, defense=4, spd=10)
    e = Entity(name=name, team="enemies", stats=stats)
    e.controller = ShieldedMiniboss()
    return e


def make_miniboss_summoner(name: str = "Caller of Bones") -> Entity:
    stats = Stats(max_hp=100, hp=100, atk=12, defense=3, spd=9)
    e = Entity(name=name, team="enemies", stats=stats)
    e.controller = SummonerMiniboss(cadence=3, adds=2)
    return e


def make_miniboss_enraged(name: str = "Bloodreaver") -> Entity:
    stats = Stats(max_hp=140, hp=140, atk=14, defense=2, spd=8)
    e = Entity(name=name, team="enemies", stats=stats)
    e.controller = EnragedMiniboss(threshold=0.5, atk_multiplier=1.5)
    return e


def make_miniboss_reflect(name: str = "Mirror Shade") -> Entity:
    stats = Stats(max_hp=110, hp=110, atk=13, defense=3, spd=11)
    e = Entity(name=name, team="enemies", stats=stats)
    e.controller = ReflectMiniboss(cooldown=3, duration=2, ratio=0.5)
    return e

