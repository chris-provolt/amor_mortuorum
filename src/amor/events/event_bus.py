import logging
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, DefaultDict, Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    """Generic event container for broadcasting within the application.

    Attributes:
        name: Event type/name string, typically from EventType.
        payload: Arbitrary payload associated with the event.
    """
    name: str
    payload: Dict[str, Any]


class EventBus:
    """A lightweight thread-safe publish/subscribe event bus.

    Subscribers can register callbacks for specific event names. When an event is
    published, all callbacks registered for that event name will be invoked in
    registration order.
    """

    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Callable[[Event], None]]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """Subscribe a callback for a given event name.

        Args:
            event_name: The event name to listen for.
            callback: A function accepting a single Event argument.
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._subs[event_name].append(callback)
            logger.debug("Subscribed %s to '%s'", getattr(callback, "__name__", str(callback)), event_name)

    def unsubscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """Unsubscribe a callback from a given event name.

        Args:
            event_name: The event name to remove the callback from.
            callback: The previously subscribed callback.
        """
        with self._lock:
            if event_name in self._subs and callback in self._subs[event_name]:
                self._subs[event_name].remove(callback)
                logger.debug("Unsubscribed %s from '%s'", getattr(callback, "__name__", str(callback)), event_name)

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all registered subscribers.

        Args:
            event_name: The event name to publish.
            payload: A dictionary payload.
        """
        event = Event(name=event_name, payload=payload)
        with self._lock:
            subs = list(self._subs.get(event_name, []))
        logger.debug("Publishing event '%s' to %d subscribers with payload: %s", event_name, len(subs), payload)
        for cb in subs:
            try:
                cb(event)
            except Exception:  # pragma: no cover - guard rail
                logger.exception("Unhandled exception in event subscriber for '%s'", event_name)


# Module-level singleton for convenience
_GLOBAL_BUS: EventBus = EventBus()


def get_event_bus() -> EventBus:
    """Return the global EventBus singleton.
    This keeps basic systems decoupled while making pub/sub easy to access.
    """
    return _GLOBAL_BUS
