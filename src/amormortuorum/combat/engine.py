from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from .damage import DamageCalculator
from .entities import Combatant
from .log import CombatLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttackResult:
    """Result of an attack action."""

    attacker: str
    defender: str
    damage: int
    defender_hp_before: int
    defender_hp_after: int
    defeated: bool


class CombatEngine:
    """Core combat interactions for FF1-style turn-based attacks."""

    def __init__(self, damage_calculator: DamageCalculator | None = None, log: CombatLog | None = None) -> None:
        self.damage_calculator = damage_calculator or DamageCalculator()
        self.log = log or CombatLog()

    def attack(
        self,
        attacker: Combatant,
        defender: Combatant,
        rng: random.Random | None = None,
        variance: float | None = None,
    ) -> AttackResult:
        """Perform a basic attack, applying damage and logging defeat if it occurs.

        Args:
            attacker: The attacking combatant.
            defender: The defending combatant.
            rng: Optional RNG for deterministic tests.
            variance: Optional override of damage variance for this attack only.

        Returns:
            AttackResult summarizing the outcome.
        """
        if attacker is None or defender is None:
            raise ValueError("attacker and defender must be provided")
        if not attacker.alive:
            logger.warning("%s attempted to attack while defeated; no action taken.", attacker.name)
            # No-op attack; guaranteed zero damage
            return AttackResult(
                attacker=attacker.name,
                defender=defender.name,
                damage=0,
                defender_hp_before=defender.hp,
                defender_hp_after=defender.hp,
                defeated=not defender.alive,
            )

        # Optionally override variance just for this call.
        if variance is not None:
            calc = DamageCalculator(variance=variance)
        else:
            calc = self.damage_calculator

        # Compute damage and apply to defender.
        dmg = calc.compute_damage(attacker.atk, defender.df, rng=rng)
        before = defender.hp
        applied = defender.take_damage(dmg)
        after = defender.hp

        # Log the attack event.
        self.log.add(
            "attack",
            f"{attacker.name} attacks {defender.name} for {applied} damage (HP {before}->{after}).",
            attacker=attacker.name,
            defender=defender.name,
            damage=applied,
            hp_before=before,
            hp_after=after,
        )

        defeated = (after == 0)
        if defeated:
            self.log.add(
                "defeat",
                f"{defender.name} was defeated by {attacker.name}.",
                attacker=attacker.name,
                defender=defender.name,
            )
        return AttackResult(
            attacker=attacker.name,
            defender=defender.name,
            damage=applied,
            defender_hp_before=before,
            defender_hp_after=after,
            defeated=defeated,
        )
