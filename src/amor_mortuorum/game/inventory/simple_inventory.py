from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from ..interfaces import InventoryProtocol


class SimpleInventory(InventoryProtocol):
    """A minimal, engine-agnostic inventory for core logic and tests.

    - Stores item counts as integers keyed by item_id string
    - Raises ValueError when asked to consume more than available
    - Thread-safety is out-of-scope; the main game loop is single-threaded
    """

    def __init__(self, items: Dict[str, int] | None = None) -> None:
        self._items: Dict[str, int] = dict(items or {})

    def get_item_count(self, item_id: str) -> int:
        return int(self._items.get(item_id, 0))

    def add_item(self, item_id: str, qty: int = 1) -> None:
        if qty < 0:
            raise ValueError("qty must be non-negative")
        if qty == 0:
            return
        self._items[item_id] = self.get_item_count(item_id) + qty

    def consume_item(self, item_id: str, qty: int = 1) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        current = self.get_item_count(item_id)
        if current < qty:
            raise ValueError(
                f"Insufficient quantity for item '{item_id}': have {current}, need {qty}"
            )
        remaining = current - qty
        if remaining:
            self._items[item_id] = remaining
        else:
            # Remove key to keep dict sparse
            self._items.pop(item_id, None)


@dataclass
class ActorWithInventory:
    """Thin helper to model an actor that possesses an inventory.

    The real project likely has a richer Actor/Entity system; this class is an
    adapter for tests and domain-logic that only need inventory access.
    """

    name: str
    inventory: SimpleInventory = field(default_factory=SimpleInventory)
