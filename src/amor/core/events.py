from typing import Callable, Dict, List, Any, DefaultDict
from collections import defaultdict


class EventBus:
    """Simple publish/subscribe event bus for game notifications and domain events.

    - Subscribers register a callable per event type string.
    - Publishers emit events with optional payload dicts.
    - Bus stores a rolling history of events for diagnostics/testing.
    """

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)
        self._history: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        if not callable(handler):
            raise TypeError("Event handler must be callable")
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        event = {"type": event_type, **payload}
        # Store in history for testability and debugging
        self._history.append(event)
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                # Handlers should never break the game loop
                # Deliberately swallow exceptions; production systems could log here
                pass

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)
