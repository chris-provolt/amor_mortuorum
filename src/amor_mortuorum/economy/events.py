import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Type, TypeVar, Generic, Any


T = TypeVar("T")


class EventBus:
    """Simple thread-safe in-process event bus for game events.

    Subscribers are keyed by event class; events are emitted by instance.
    This is intentionally lightweight and synchronous to keep determinism for tests.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[Type[Any], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)  # type: ignore[arg-type]

    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
                if not handlers:
                    self._subscribers.pop(event_type, None)

    def emit(self, event: Any) -> None:
        with self._lock:
            for event_type, handlers in list(self._subscribers.items()):
                if isinstance(event, event_type):
                    for h in list(handlers):
                        h(event)


@dataclass(frozen=True)
class GoldChangedEvent:
    old_amount: int
    new_amount: int
    delta: int
    reason: str  # e.g., "combat", "chest", "purchase", "grant", "adjust"


@dataclass(frozen=True)
class PurchaseCompletedEvent:
    item_id: str
    cost: int
    remaining_gold: int


@dataclass(frozen=True)
class PurchaseFailedEvent:
    item_id: str
    cost: int
    reason: str
    current_gold: int
