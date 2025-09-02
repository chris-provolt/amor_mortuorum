import logging
from threading import RLock
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """A lightweight, thread-safe publish/subscribe event bus.

    - Subscribers register handlers for event names (strings).
    - Emit broadcasts payloads to all handlers of that event.

    Intended for decoupling UI components and managers.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._handlers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event: str, handler: Callable[[Any], None]) -> None:
        """Subscribe a handler to an event name."""
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)
            logger.debug("Subscribed handler %s to event '%s'", getattr(handler, "__name__", str(handler)), event)

    def unsubscribe(self, event: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe a handler from an event name. Silently ignores if not present."""
        with self._lock:
            if event in self._handlers and handler in self._handlers[event]:
                self._handlers[event].remove(handler)
                logger.debug("Unsubscribed handler %s from event '%s'", getattr(handler, "__name__", str(handler)), event)

    def emit(self, event: str, payload: Any = None) -> None:
        """Emit an event with an optional payload to all subscribed handlers.

        Handlers exceptions are caught and logged, allowing other handlers to still run.
        """
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        logger.debug("Emitting event '%s' to %d handlers with payload: %r", event, len(handlers), payload)
        for handler in handlers:
            try:
                handler(payload)
            except Exception as exc:  # noqa: BLE001 - we want to log any exception from handlers
                logger.exception("Error in event handler for '%s': %s", event, exc)
