"""Run state: the party, current floor and seed for one descent.

Bridges the runtime entities with ``persistence.RunState`` and owns the death
and resurrection-token rules.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ..data import MAX_FLOOR, GameData
from ..persistence import MetaState, RunState
from .entities import Player, new_player

logger = logging.getLogger(__name__)

RESURRECTION_TOKEN_ID = "res_token"
STARTING_KIT = {"potion_small": 2, RESURRECTION_TOKEN_ID: 1}


@dataclass
class DeathResult:
    revived: bool
    floor: int
    message: str


@dataclass
class RunSummary:
    floor_reached: int
    gold: int
    cause: str
    revived: bool = False
    victory: bool = False


@dataclass
class Run:
    seed: int
    floor: int = 1
    party: List[Player] = field(default_factory=list)
    steps_since_encounter: int = 0
    encounters: int = 0
    in_graveyard: bool = True

    # Convenience

    @property
    def leader(self) -> Player:
        return self.party[0]

    @property
    def alive(self) -> bool:
        return any(p.is_alive for p in self.party)

    def descend(self) -> int:
        """Advance to the next floor (capped at MAX_FLOOR) and reset step counters."""
        self.floor = min(MAX_FLOOR, self.floor + 1)
        self.steps_since_encounter = 0
        self.encounters = 0
        logger.info("Descended to floor %d", self.floor)
        return self.floor

    def has_token(self) -> bool:
        return any(p.has_item(RESURRECTION_TOKEN_ID) for p in self.party)

    def on_death(self, meta: MetaState, data: GameData) -> DeathResult:
        """Resolve a party wipe.

        With a Resurrection Token: consume it, revive the party at 1 HP and
        return to the Graveyard. Without one: the run ends; ``meta`` records
        the deepest floor reached.
        """
        meta.deepest_floor = max(meta.deepest_floor, self.floor)
        for p in self.party:
            if p.has_item(RESURRECTION_TOKEN_ID):
                p.inventory.remove(data.item(RESURRECTION_TOKEN_ID), 1)
                for member in self.party:
                    member.stats.hp = max(1, member.stats.hp)
                self.in_graveyard = True
                logger.info("Resurrection Token consumed; party returns to the Graveyard")
                return DeathResult(
                    revived=True,
                    floor=self.floor,
                    message="The token burns away. You wake among the graves.",
                )
        logger.info("Party fell on floor %d with no token; run over", self.floor)
        return DeathResult(
            revived=False,
            floor=self.floor,
            message=f"You fell on floor {self.floor}. The Veil keeps what it takes.",
        )

    def summary(self, cause: str, revived: bool = False, victory: bool = False) -> RunSummary:
        return RunSummary(
            floor_reached=self.floor,
            gold=sum(p.gold for p in self.party),
            cause=cause,
            revived=revived,
            victory=victory,
        )

    # Persistence

    def to_run_state(self) -> RunState:
        return RunState(
            floor=self.floor,
            in_graveyard=self.in_graveyard,
            rng_seed=self.seed,
            party=[p.to_dict() for p in self.party],
            steps_since_encounter=self.steps_since_encounter,
        )

    @staticmethod
    def from_run_state(state: RunState) -> "Run":
        return Run(
            seed=state.rng_seed,
            floor=state.floor,
            party=[Player.from_dict(p) for p in state.party],
            steps_since_encounter=state.steps_since_encounter,
            in_graveyard=state.in_graveyard,
        )


def new_run(
    data: GameData, seed: int, name: str = "Wanderer", meta: Optional[MetaState] = None
) -> Run:
    """Start a fresh run at floor 1 with the starting kit."""
    player = new_player(name)
    for item_id, qty in STARTING_KIT.items():
        player.inventory.add(data.item(item_id), qty)
    run = Run(seed=seed, floor=1, party=[player])
    logger.info("New run started: seed=%d", seed)
    return run
