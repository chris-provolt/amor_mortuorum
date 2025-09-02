from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Iterable

from items.base import Item


class InventoryFullError(Exception):
    pass


class ItemNotInInventoryError(Exception):
    pass


@dataclass
class Inventory:
    """Simple inventory container with capacity and basic operations.

    - add: add single item
    - extend: add multiple items
    - remove: remove a specific item instance
    - contains: check presence by object identity
    - list: expose a copy of items
    """

    capacity: int = 30
    _items: List[Item] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Inventory capacity must be > 0")

    @property
    def items(self) -> List[Item]:
        return list(self._items)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)

    def has_space(self, count: int = 1) -> bool:
        return len(self._items) + count <= self.capacity

    def add(self, item: Item) -> None:
        if not self.has_space(1):
            raise InventoryFullError("Inventory is full")
        self._items.append(item)

    def extend(self, items: Iterable[Item]) -> None:
        items = list(items)
        if not self.has_space(len(items)):
            raise InventoryFullError("Not enough inventory space")
        self._items.extend(items)

    def remove(self, item: Item) -> None:
        try:
            self._items.remove(item)
        except ValueError as e:
            raise ItemNotInInventoryError("Item not in inventory") from e

    def pop(self, index: int = -1) -> Item:
        return self._items.pop(index)

    def contains(self, item: Item) -> bool:
        return item in self._items

    def clear(self) -> None:  # pragma: no cover - not used in tests
        self._items.clear()

    def find_first_by_id(self, item_id: str) -> Optional[Item]:  # pragma: no cover - optional helper
        for it in self._items:
            if it.id == item_id:
                return it
        return None
