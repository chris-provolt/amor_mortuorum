from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .models import Party
from .actions import AttackAction, DefendAction, FleeAction, FleeResult
from ..config import CombatConfig
from ..utils.random_provider import RandomProvider

logger = logging.getLogger(__name__)


@dataclass
class CombatEngine:
    """
    Thin orchestration layer for executing combat actions.

    While a full engine would manage turn order, statuses, and targeting,
    this facade exists to cleanly expose Defend and Flee behavior and
    support unit testing.
    """

    party: Party
    enemies: Party
    rng: RandomProvider
    config: Optional[CombatConfig] = None

    def defend(self, actor_index: int) -> None:
        actor = self.party.members[actor_index]
        DefendAction().execute(actor, self.config)

    def attack(self, attacker_is_party: bool, attacker_index: int, target_is_party: bool, target_index: int, damage: int) -> int:
        """Execute a simple fixed-damage attack for test/demo purposes."""
        attacker_party = self.party if attacker_is_party else self.enemies
        target_party = self.party if target_is_party else self.enemies
        attacker = attacker_party.members[attacker_index]
        target = target_party.members[target_index]
        return AttackAction(damage).execute(attacker, target)

    def attempt_flee(self) -> FleeResult:
        action = FleeAction(self.rng, self.config)
        return action.attempt(self.party, self.enemies)
