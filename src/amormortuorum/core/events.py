from __future__ import annotations

"""
A minimal, synchronous event bus to decouple systems.
For now, it is intentionally simple: listeners are invoked in registration order.
"""
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List


Listener = Callable[[str, Dict[str, Any]], None]


class EventBus:
    """Simple publish/subscribe event bus."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, List[Listener]] = defaultdict(list)

    def on(self, event_name: str, listener: Listener) -> None:
        """Register a listener for a specific event name."""
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, payload: Dict[str, Any] | None = None) -> None:
        """Emit an event with optional payload, notifying all listeners."""
        if payload is None:
            payload = {}
        for listener in list(self._listeners.get(event_name, [])):
            listener(event_name, payload)
