from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """Lightweight, threadsafe publish/subscribe event bus.

    Provides a minimal integration point so gameplay systems can communicate
    without tight coupling. Handlers are called synchronously in emit order.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[..., Any]]] = {}
        self._lock = RLock()

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Subscribe a handler to an event channel.

        Args:
            event: Event channel name.
            handler: Callable that accepts keyword arguments of event payload.
        """
        with self._lock:
            self._handlers.setdefault(event, [])
            if handler not in self._handlers[event]:
                self._handlers[event].append(handler)
                logger.debug("Subscribed handler %s to event '%s'", handler, event)

    def unsubscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Unsubscribe a handler from an event channel."""
        with self._lock:
            handlers = self._handlers.get(event)
            if not handlers:
                return
            if handler in handlers:
                handlers.remove(handler)
                logger.debug("Unsubscribed handler %s from event '%s'", handler, event)
            if not handlers:
                del self._handlers[event]

    def clear(self) -> None:
        """Remove all handlers for all events (useful in tests)."""
        with self._lock:
            self._handlers.clear()

    def emit(self, event: str, **kwargs: Any) -> List[Any]:
        """Emit an event with payload to all subscribed handlers.

        Args:
            event: Event channel name.
            **kwargs: Arbitrary payload.

        Returns:
            List of return values from handlers (if any).
        """
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        if not handlers:
            logger.debug("Emitting '%s' with no subscribers. Payload=%s", event, kwargs)
            return []
        logger.debug("Emitting '%s' to %d handlers. Payload=%s", event, len(handlers), kwargs)
        results: List[Any] = []
        for handler in handlers:
            try:
                results.append(handler(**kwargs))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Error in handler %s for event '%s': %s", handler, event, exc)
        return results


# Global default bus (optional use)
GLOBAL_EVENT_BUS: Optional[EventBus] = None


def get_global_bus() -> EventBus:
    """Return a process-global EventBus, creating one if necessary."""
    global GLOBAL_EVENT_BUS
    if GLOBAL_EVENT_BUS is None:
        GLOBAL_EVENT_BUS = EventBus()
    return GLOBAL_EVENT_BUS
