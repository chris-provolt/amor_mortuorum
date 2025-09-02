from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class Event:
    type: str
    payload: Dict[str, Any]


class EventBus:
    """
    Minimal pub/sub event bus used to broadcast gameplay events such as SFX and music changes.
    Also stores a history for testing and analytics.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._history: List[Event] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any] | None = None) -> None:
        evt = Event(event_type, payload or {})
        self._history.append(evt)
        for h in self._subscribers.get(event_type, []):
            try:
                h(evt)
            except Exception:
                # Avoid crashing the bus due to bad handler; in production use logging.
                pass

    @property
    def history(self) -> Tuple[Event, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()
