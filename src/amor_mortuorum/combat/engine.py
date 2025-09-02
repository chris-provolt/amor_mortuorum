from __future__ import annotations

from typing import List, Optional

from .core import (
    Action,
    AttackAction,
    BattleContext,
    CombatLog,
    DamageEvent,
    Entity,
    NoopAction,
    SummonAction,
    CastReflectAction,
    ReflectStatus,
)


class BattleEngine:
    """A minimal, deterministic turn engine for tests and boss mechanics.

    Note: This is deliberately small and focused to support miniboss templates
    and unit tests. The full game can expand on top of these interfaces.
    """

    def __init__(self, party: List[Entity], enemies: List[Entity]) -> None:
        self.party: List[Entity] = party
        self.enemies: List[Entity] = enemies
        self.turn: int = 0
        self.log = CombatLog()
        self.ctx = BattleContext(self, self.log)
        for e in self.entities:
            # ensure each entity knows its team and has no stale statuses
            pass

    @property
    def entities(self) -> List[Entity]:
        return [*self.party, *self.enemies]

    def first_living_opponent(self, who: Entity) -> Optional[Entity]:
        opponents = self.party if who in self.enemies else self.enemies
        for e in opponents:
            if e.alive:
                return e
        return None

    def start_battle(self) -> None:
        # fire battle start hooks
        for e in self.entities:
            if e.controller:
                e.controller.on_battle_start(e, self.ctx)
        # initial telegraphs are already in log by controllers

    def is_battle_over(self) -> bool:
        party_alive = any(e.alive for e in self.party)
        enemies_alive = any(e.alive for e in self.enemies)
        return not (party_alive and enemies_alive)

    def living_initiative_order(self) -> List[Entity]:
        living = [e for e in self.entities if e.alive]
        # stable deterministic ordering: by SPD desc, then by creation order
        return sorted(living, key=lambda e: e.stats.spd, reverse=True)

    def step_turn(self) -> None:
        self.turn += 1
        self.log.add(f"-- Turn {self.turn} --")
        order = self.living_initiative_order()
        # Turn start hooks
        for e in order:
            if not e.alive:
                continue
            if e.controller:
                e.controller.on_turn_start(e, self.ctx)
        # Actions
        for e in order:
            if not e.alive:
                continue
            action = self._choose_action(e)
            self._execute_action(action)
            if self.is_battle_over():
                break
        # Turn end hooks and status ticking
        for e in order:
            if not e.alive:
                continue
            if e.controller:
                e.controller.on_turn_end(e, self.ctx)
            e.tick_statuses(self.ctx)
            e.remove_expired_statuses(self.ctx)

    def _choose_action(self, e: Entity) -> Action:
        if e.controller:
            return e.controller.choose_action(e, self.ctx)
        return e.choose_action(self.ctx)

    def _execute_action(self, action: Action) -> None:
        if isinstance(action, NoopAction):
            self.log.add(f"{action.actor.name} does nothing.")
            return
        if isinstance(action, AttackAction):
            attacker = action.attacker
            target = action.target
            if not attacker.alive or not target.alive:
                return
            dmg_amount = attacker.compute_attack_damage(target)
            dmg = DamageEvent(source=attacker, target=target, amount=dmg_amount)
            target.receive_damage(dmg, self.ctx)
            return
        if isinstance(action, SummonAction):
            self._do_summon(action)
            return
        if isinstance(action, CastReflectAction):
            self._do_cast_reflect(action)
            return
        # unknown action type fallback
        self.log.add("Unknown action; skipped.")

    def _do_summon(self, action: SummonAction) -> None:
        if not action.summoner.alive:
            return
        # Create generic adds with low stats
        for i in range(action.count):
            add = Entity(
                name=f"{action.summoner.name}'s Add {i+1}",
                team=action.summoner.team,
                stats=self._minion_stats(),
            )
            self.log.add(f"{action.summoner.name} summons {add.name}!")
            # Insert after boss in enemies list to keep ordering stable
            if action.summoner in self.enemies:
                self.enemies.append(add)
            else:
                self.party.append(add)

    def _do_cast_reflect(self, action: CastReflectAction) -> None:
        caster = action.caster
        if not caster.alive:
            return
        caster.add_status(ReflectStatus(ratio=action.ratio, duration=action.duration), self.ctx)
        self.log.add(f"{caster.name} is wreathed in a Mirror Veil!")

    @staticmethod
    def _minion_stats():
        from .core import Stats

        return Stats(max_hp=10, hp=10, atk=3, defense=0, spd=5)

