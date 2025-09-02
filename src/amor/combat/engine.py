from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol, Sequence, Tuple
import logging

from ..core.party import Party, PartyMember

logger = logging.getLogger(__name__)


class Combatant(Protocol):
    """Protocol for any combatant (player or enemy)."""

    @property
    def name(self) -> str:  # pragma: no cover - Protocol
        ...

    @property
    def is_alive(self) -> bool:  # pragma: no cover - Protocol
        ...

    @property
    def spd(self) -> int:  # pragma: no cover - Protocol
        ...


@dataclass
class SimpleEnemy:
    """Minimal enemy for testing/demo purposes."""

    name: str
    spd: int = 8
    alive: bool = True

    @property
    def is_alive(self) -> bool:
        return self.alive


@dataclass
class TurnActor:
    name: str
    is_player: bool
    spd: int


class CombatEngine:
    """Turn-based combat engine.

    This engine focuses on turn ordering and actor iteration. Actions/skills are
    out of scope here. The engine respects the current party composition, looping
    only over existing, alive party members, and supports up to 4 party slots.
    """

    def build_turn_order(
        self,
        party: Party,
        enemies: Sequence[Combatant],
        include_dead: bool = False,
    ) -> List[TurnActor]:
        """Construct a single-round turn order based on SPD, descending.

        Args:
            party: The player party.
            enemies: Enemy combatants.
            include_dead: If True, include dead actors (mostly for debugging); otherwise excluded.
        """
        actors: List[TurnActor] = []

        def party_iter() -> Iterable[PartyMember]:
            return party.iter_all_members() if include_dead else party.iter_active_members()

        for m in party_iter():
            actors.append(TurnActor(name=m.name, is_player=True, spd=m.stats.spd))
        for e in enemies:
            if include_dead or e.is_alive:
                actors.append(TurnActor(name=e.name, is_player=False, spd=e.spd))
        # Sort by SPD descending, stable tie-breaker by preserving insertion order
        actors.sort(key=lambda a: a.spd, reverse=True)
        logger.debug("Turn order: %s", [(a.name, a.spd) for a in actors])
        return actors

    def run_round(
        self, party: Party, enemies: Sequence[Combatant]
    ) -> List[Tuple[str, str]]:
        """Run a single round, returning (actor_name, action_desc) tuples.

        This stub performs no real actions; it demonstrates correct iteration over
        the party and enemies. In the future, this would integrate with input,
        AI, skills, and damage resolution.
        """
        actions: List[Tuple[str, str]] = []
        for actor in self.build_turn_order(party, enemies, include_dead=False):
            # Placeholder action
            desc = "acts"
            logger.info("%s %s", actor.name, desc)
            actions.append((actor.name, desc))
        return actions
