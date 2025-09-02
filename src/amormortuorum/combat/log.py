from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CombatEvent:
    """A log event emitted during combat.

    Common event types: "attack", "defeat".
    """

    type: str
    message: str
    data: Optional[Dict[str, Any]] = None


class CombatLog:
    """Lightweight in-memory combat log to capture notable events."""

    def __init__(self) -> None:
        self._events: List[CombatEvent] = []

    def add(self, event_type: str, message: str, **data: Any) -> None:
        ev = CombatEvent(type=event_type, message=message, data=data or None)
        self._events.append(ev)
        # Forward to standard logging for visibility if configured.
        if event_type == "defeat":
            logging.getLogger(__name__).info(message)
        else:
            logging.getLogger(__name__).debug(message)

    def events(self) -> List[CombatEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
