import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """Minimal synchronous pub/sub event bus.

    Designed to decouple systems such as RunState and Shop without external deps.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Optional[dict]], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Optional[dict]], None]) -> None:
        logger.debug("Subscribing to event '%s': %s", event_name, callback)
        self._subscribers.setdefault(event_name, []).append(callback)

    def publish(self, event_name: str, payload: Optional[dict] = None) -> None:
        logger.debug("Publishing event '%s' to %d subscribers", event_name, len(self._subscribers.get(event_name, [])))
        for cb in self._subscribers.get(event_name, []):
            try:
                cb(payload)
            except Exception as exc:
                logger.exception("Error in event subscriber for '%s': %s", event_name, exc)
