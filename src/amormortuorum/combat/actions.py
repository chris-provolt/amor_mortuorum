from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .models import Actor, Party
from ..config import CombatConfig
from ..utils.random_provider import RandomProvider

logger = logging.getLogger(__name__)


@dataclass
class AttackAction:
    """
    A simple attack dealing a fixed amount of damage to a single target.

    This is intentionally minimal to facilitate testing of Defend mechanics
    without coupling to a full damage formula.
    """

    damage: int

    def execute(self, attacker: Actor, target: Actor) -> int:
        if self.damage < 0:
            raise ValueError("Attack damage cannot be negative")
        logger.debug("%s attacks %s for %d base damage", attacker.name, target.name, self.damage)
        return target.take_damage(self.damage)


@dataclass
class DefendAction:
    """
    Defend sets a temporary damage multiplier on the user that applies only
    to the next instance of damage received. Typical multiplier is 0.5.
    """

    multiplier: Optional[float] = None

    def execute(self, user: Actor, config: Optional[CombatConfig] = None) -> None:
        m = self.multiplier
        if m is None:
            m = (config.defend_multiplier if config else CombatConfig.default().defend_multiplier)
        logger.debug("%s uses Defend (multiplier=%.3f)", user.name, m)
        user.apply_defend(m)


@dataclass
class FleeResult:
    success: bool
    probability: float


@dataclass
class FleeAction:
    """
    Attempt to flee from combat.

    Success probability scales with the ratio of party SPD to enemy SPD.

    Let ratio = party_spd / max(1, enemy_spd)
    p = clamp(min, max, base + scale * (ratio - 1))

    Defaults are provided by CombatConfig.
    """

    rng: RandomProvider
    config: Optional[CombatConfig] = None

    def _probability(self, party: Party, enemies: Party) -> float:
        cfg = self.config or CombatConfig.default()
        party_spd = party.aggregate_spd(cfg.flee_spd_aggregation)
        enemy_spd = enemies.aggregate_spd(cfg.flee_spd_aggregation)

        # Auto-success if there are no enemies alive
        if enemies.is_wiped():
            return 1.0

        ratio = party_spd / max(1.0, enemy_spd)
        p = cfg.flee_base + cfg.flee_scale * (ratio - 1.0)
        # Clamp to [min, max]
        p = max(cfg.flee_min, min(cfg.flee_max, p))
        logger.debug(
            "Flee probability computed: party_spd=%.3f, enemy_spd=%.3f, ratio=%.3f, p=%.3f",
            party_spd,
            enemy_spd,
            ratio,
            p,
        )
        return p

    def attempt(self, party: Party, enemies: Party) -> FleeResult:
        probability = self._probability(party, enemies)
        roll = self.rng.random()
        success = roll < probability
        logger.debug("Flee attempt: roll=%.5f, probability=%.5f, success=%s", roll, probability, success)
        return FleeResult(success=success, probability=probability)
