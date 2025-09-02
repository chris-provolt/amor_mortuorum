from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol, Union

logger = logging.getLogger(__name__)


class SupportsTurnActor(Protocol):
    """Protocol for combat actors used by TurnQueue.

    An actor must expose:
    - spd: numeric speed value (higher is faster)
    - is_alive: boolean property or method indicating whether actor can act
    - id: a deterministic, stable identifier (str | int) to break SPD ties

    Implementations may provide additional fields; only these are required.
    """

    id: Union[str, int]
    spd: Union[int, float]

    @property
    def is_alive(self) -> bool:  # pragma: no cover - enforced via tests against implementation
        ...


@dataclass
class MinimalActor:
    """A minimal concrete Actor for testing or simple simulations.

    Attributes:
        id: Stable identifier used for deterministic tie-breaking.
        name: Human-readable label.
        spd: Speed; higher acts earlier in the round.
        hp: Hit points; hp > 0 means alive.
    """

    id: Union[str, int]
    name: str
    spd: Union[int, float]
    hp: int = 1

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def kill(self) -> None:
        self.hp = 0

    def __repr__(self) -> str:
        return f"MinimalActor(id={self.id!r}, name={self.name!r}, spd={self.spd}, hp={self.hp})"


class TurnQueue:
    """Deterministic SPD-based turn order for FF1-style rounds.

    Features:
    - Orders actors by SPD descending each round.
    - Skips dead actors both when building and at selection time.
    - Recalculates order at the start of every round (so SPD changes between rounds take effect).
    - Deterministic tie-breaking using a stable attribute (default: actor.id).

    Usage:
        tq = TurnQueue([actors...])
        actor = tq.next_actor()  # returns the next actor to act
        if actor is None:        # no alive actors remain
            ...

    Notes:
    - If all actors are dead, next_actor() returns None.
    - If an actor dies mid-round before their turn, they will be skipped when encountered.
    - Adding or removing actors affects subsequent rounds (not the in-progress ordering).
    """

    def __init__(
        self,
        actors: Iterable[SupportsTurnActor],
        *,
        tie_breaker_attr: str = "id",
    ) -> None:
        self._actors: List[SupportsTurnActor] = list(actors)
        self._tie_breaker_attr = tie_breaker_attr
        # Stable join order fallback based on order provided; key by Python id for robustness
        self._join_order_by_pyid = {id(a): i for i, a in enumerate(self._actors)}
        self._queue: List[SupportsTurnActor] = []
        self.round_number: int = 0
        # Build the first round immediately for determinism
        self._rebuild_for_new_round()

    # --------------- Public API ---------------

    def add_actor(self, actor: SupportsTurnActor) -> None:
        """Add an actor to the roster. Will take effect next round.
        The stable join-order fallback is updated for deterministic tiebreaking.
        """
        self._actors.append(actor)
        self._join_order_by_pyid[id(actor)] = len(self._join_order_by_pyid)
        logger.debug("Added actor %s. Roster size now %d", actor, len(self._actors))

    def remove_actor(self, actor: SupportsTurnActor) -> None:
        """Remove an actor from the roster. Safe to call mid-round; the actor
        will be removed from future rounds. If still present in the current queue,
        it will be skipped when encountered.
        """
        try:
            self._actors.remove(actor)
            logger.debug("Removed actor %s. Roster size now %d", actor, len(self._actors))
        except ValueError:
            logger.debug("Attempted to remove actor %s but it was not in roster", actor)

    def next_actor(self) -> Optional[SupportsTurnActor]:
        """Return the next alive actor to act. If no alive actors exist, returns None.

        Rebuilds the queue at the start of each new round. If the next queued actor
        is now dead, it will be skipped and the next alive actor is returned.
        """
        # If there are no alive actors at all, immediately return None
        if not any(self._is_alive(a) for a in self._actors):
            logger.debug("No alive actors. next_actor() -> None")
            return None

        # If the round queue is empty (e.g., at start or after completing a round), rebuild
        if not self._queue:
            self._rebuild_for_new_round()
            if not self._queue:  # could be empty if everyone died between rounds
                logger.debug("Queue empty after rebuild; no alive actors. next_actor() -> None")
                return None

        while self._queue:
            nxt = self._queue.pop(0)
            if self._is_alive(nxt):
                logger.debug("Round %d: next actor is %s", self.round_number, nxt)
                return nxt
            else:
                logger.debug("Skipped dead actor %s during round %d", nxt, self.round_number)

        # If we exhausted the queue (e.g., due to skipping dead), start a new round recursively
        logger.debug("Queue exhausted due to skips; recursing into next round")
        return self.next_actor()

    # --------------- Internal helpers ---------------

    def _rebuild_for_new_round(self) -> None:
        alive = [a for a in self._actors if self._is_alive(a)]
        # Sort: SPD descending, tie by deterministic key (ascending)
        self._queue = sorted(alive, key=self._sort_key)
        self.round_number += 1
        logger.debug(
            "Built round %d with %d actors (alive=%d/%d): %s",
            self.round_number,
            len(self._queue),
            len(alive),
            len(self._actors),
            self._queue,
        )

    def _sort_key(self, actor: SupportsTurnActor):
        spd = getattr(actor, "spd", None)
        if spd is None:
            raise ValueError(f"Actor {actor!r} missing required 'spd' attribute")
        # Python sorts ascending, so we invert SPD for descending order
        neg_spd = -float(spd)

        # Primary deterministic tie-breaker by provided attribute (default: 'id')
        if hasattr(actor, self._tie_breaker_attr):
            tie = getattr(actor, self._tie_breaker_attr)
        else:
            # Fallback: stable join order at time of addition
            tie = self._join_order_by_pyid.get(id(actor), 0)
        return (neg_spd, tie)

    @staticmethod
    def _is_alive(actor: SupportsTurnActor) -> bool:
        # Allow is_alive either as property or method
        val = getattr(actor, "is_alive")
        return val() if callable(val) else bool(val)


__all__ = [
    "SupportsTurnActor",
    "MinimalActor",
    "TurnQueue",
]
