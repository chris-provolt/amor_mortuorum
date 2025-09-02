from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CombatEvent:
    """Represents a single combat log entry.

    Attributes:
        turn_index: Turn number starting at 1 for the first player/enemy turn in a battle.
        actor: Identifier/name of the acting entity (e.g., "Warrior" or entity id).
        action: Action name (e.g., "Attack", "Firebolt", "Defend", "Poison").
        target: Identifier/name of the target entity (if any).
        value: Numeric value of the action outcome (damage/heal). Positive numbers for damage by default.
        tags: A set of semantic tags that describe the event, e.g., {"damage"}, {"heal"}, {"miss"}, {"buff"}.
        message: A pre-rendered human-readable message. If empty, a message will be synthesized by the log.
        timestamp: Monotonic timestamp when the event was recorded.
    """

    turn_index: int
    actor: str
    action: str
    target: Optional[str] = None
    value: Optional[int] = None
    tags: Tuple[str, ...] = field(default_factory=tuple)
    message: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    def with_message(self, msg: str) -> "CombatEvent":
        return CombatEvent(
            turn_index=self.turn_index,
            actor=self.actor,
            action=self.action,
            target=self.target,
            value=self.value,
            tags=self.tags,
            message=msg,
            timestamp=self.timestamp,
        )


class CombatLog:
    """In-memory combat log that persists for the duration of a battle.

    - Keeps a finite history (capacity) to avoid unbounded growth.
    - Provides utilities to add events, fetch recent entries, and paginate.

    The log is intended to be reset when a battle ends via clear() or start_new_battle().
    """

    def __init__(self, capacity: int = 1000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._events: List[CombatEvent] = []
        self._battle_id: int = 0
        logger.debug("CombatLog initialized with capacity=%d", capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def battle_id(self) -> int:
        return self._battle_id

    def start_new_battle(self) -> None:
        """Clear the log for a new battle, incrementing the battle_id for traceability."""
        self._events.clear()
        self._battle_id += 1
        logger.info("Started new battle: battle_id=%d", self._battle_id)

    def clear(self) -> None:
        """Clear current battle log without modifying battle_id."""
        logger.debug("Clearing combat log entries (count=%d)", len(self._events))
        self._events.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._events)

    def _synthesize_message(self, ev: CombatEvent) -> str:
        # Basic message synthesis; games can replace/extend this formatting.
        tags = set(ev.tags)
        if "miss" in tags:
            base = f"{ev.actor} uses {ev.action} on {ev.target or '—'}: Miss!"
        elif "heal" in tags:
            amt = 0 if ev.value is None else abs(ev.value)
            base = f"{ev.actor} heals {ev.target or ev.actor} for {amt} HP"
        elif "buff" in tags:
            base = f"{ev.actor} buffs {ev.target or ev.actor} with {ev.action}"
        elif "debuff" in tags:
            base = f"{ev.actor} inflicts {ev.action} on {ev.target or '—'}"
        else:
            # Default to damage-like action
            amt = "?" if ev.value is None else abs(ev.value)
            base = f"{ev.actor} uses {ev.action} on {ev.target or '—'} for {amt}"
            if "damage" in tags:
                base += " dmg"
        if "crit" in tags:
            base += " (CRIT)"
        return base

    def add_event(
        self,
        *,
        turn_index: int,
        actor: str,
        action: str,
        target: Optional[str] = None,
        value: Optional[int] = None,
        tags: Optional[Sequence[str]] = None,
        message: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> CombatEvent:
        """Add a combat event to the log.

        Args:
            turn_index: Turn number of this event.
            actor: Acting entity.
            action: Action name.
            target: Target entity (if any).
            value: Numeric outcome (damage/heal/etc.). Positive numbers are ok; tags inform semantics.
            tags: Sequence of tags (e.g., ["damage", "crit"]).
            message: Custom human-readable message overrides auto synthesis.
            timestamp: Optional timestamp override (testing); defaults to monotonic time.

        Returns:
            The CombatEvent instance stored in the log.
        """
        ev = CombatEvent(
            turn_index=turn_index,
            actor=actor,
            action=action,
            target=target,
            value=value,
            tags=tuple(tags or ()),
            message=message or "",
            timestamp=time.monotonic() if timestamp is None else timestamp,
        )
        if not ev.message:
            ev = ev.with_message(self._synthesize_message(ev))
        self._events.append(ev)
        # Enforce capacity (drop oldest)
        if len(self._events) > self._capacity:
            dropped = len(self._events) - self._capacity
            if dropped > 0:
                del self._events[0:dropped]
                logger.debug("CombatLog capacity exceeded, dropped=%d old events", dropped)
        logger.debug("Added CombatEvent: %s", ev)
        return ev

    def events(self) -> List[CombatEvent]:
        return list(self._events)

    def get_recent(self, n: int) -> List[CombatEvent]:
        if n <= 0:
            return []
        return self._events[-n:]

    def last_action_by(self, actor: str) -> Optional[CombatEvent]:
        for ev in reversed(self._events):
            if ev.actor == actor:
                return ev
        return None

    def iter_range(self, start: int, end: int) -> Iterable[CombatEvent]:
        """Iterate events in [start, end) indices from the beginning of the current battle log."""
        return iter(self._events[start:end])

    def to_dict(self) -> dict:
        return {
            "battle_id": self._battle_id,
            "capacity": self._capacity,
            "events": [asdict(e) for e in self._events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CombatLog":
        log = cls(capacity=int(data.get("capacity", 1000)))
        log._battle_id = int(data.get("battle_id", 0))
        for item in data.get("events", []):
            ev = CombatEvent(
                turn_index=item["turn_index"],
                actor=item["actor"],
                action=item["action"],
                target=item.get("target"),
                value=item.get("value"),
                tags=tuple(item.get("tags", ()) or ()),
                message=item.get("message", ""),
                timestamp=float(item.get("timestamp", time.monotonic())),
            )
            log._events.append(ev)
        return log


class PagedLogViewModel:
    """View model for paginating through a CombatLog.

    Provides a UI-friendly state with paging and a toggle to enter/exit history mode.

    - When history_mode is False: always shows the latest page.
    - When history_mode is True: prev/next page navigation is enabled.
    """

    def __init__(self, log: CombatLog, page_size: int = 10) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.log = log
        self.page_size = page_size
        self.history_mode = False
        self._page_index = 0  # 0 means the first page (oldest); we default to last when not in history mode
        logger.debug("PagedLogViewModel created page_size=%d", page_size)

    @property
    def total_pages(self) -> int:
        if len(self.log) == 0:
            return 1
        pages, rem = divmod(len(self.log), self.page_size)
        return pages + (1 if rem else 0)

    @property
    def last_page_index(self) -> int:
        return max(0, self.total_pages - 1)

    @property
    def page_index(self) -> int:
        if not self.history_mode:
            return self.last_page_index
        return min(max(0, self._page_index), self.last_page_index)

    def toggle_history_mode(self) -> None:
        self.history_mode = not self.history_mode
        if not self.history_mode:
            # Snap to latest when exiting history mode
            self._page_index = self.last_page_index
        logger.debug("History mode set to %s", self.history_mode)

    def next_page(self) -> None:
        if not self.history_mode:
            return
        self._page_index = min(self.last_page_index, self.page_index + 1)
        logger.debug("Navigated to next page index=%d", self._page_index)

    def prev_page(self) -> None:
        if not self.history_mode:
            return
        self._page_index = max(0, self.page_index - 1)
        logger.debug("Navigated to prev page index=%d", self._page_index)

    def go_to_first(self) -> None:
        if not self.history_mode:
            return
        self._page_index = 0
        logger.debug("Navigated to first page")

    def go_to_last(self) -> None:
        if not self.history_mode:
            return
        self._page_index = self.last_page_index
        logger.debug("Navigated to last page")

    def get_page_events(self) -> List[CombatEvent]:
        if len(self.log) == 0:
            return []
        start = self.page_index * self.page_size
        end = start + self.page_size
        return list(self.log.iter_range(start, end))

    def get_page_lines(self) -> List[str]:
        events = self.get_page_events()
        return [e.message for e in events]

    def get_recent_lines(self, n: int) -> List[str]:
        return [e.message for e in self.log.get_recent(n)]
