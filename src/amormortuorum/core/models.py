from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List

from .errors import CryptFullError, InvalidIndexError


@dataclass
class Item:
    """Simple item model.

    In a full implementation this would include additional fields such as
    rarity, stack size, effects, value, etc. For the Crypt feature we only
    need basic identity and display name.
    """

    id: str
    name: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Item":
        return Item(id=data["id"], name=data["name"])


class Inventory:
    """Player inventory container.

    For the purposes of this feature there is no capacity on inventory and no
    stack behavior; items are stored as a flat list.
    """

    def __init__(self, items: List[Item] | None = None) -> None:
        self._items: List[Item] = list(items) if items else []

    def add_item(self, item: Item) -> None:
        self._items.append(item)

    def remove_index(self, index: int) -> Item:
        try:
            return self._items.pop(index)
        except IndexError as exc:
            raise InvalidIndexError(f"Inventory index out of range: {index}") from exc

    def peek_index(self, index: int) -> Item:
        try:
            return self._items[index]
        except IndexError as exc:
            raise InvalidIndexError(f"Inventory index out of range: {index}") from exc

    def list_items(self) -> List[Item]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)


class Crypt:
    """Persistent Crypt storage with capacity limit."""

    def __init__(self, capacity: int, items: List[Item] | None = None) -> None:
        if capacity <= 0:
            raise ValueError("Crypt capacity must be positive")
        self.capacity = capacity
        self._items: List[Item] = list(items) if items else []

    def can_store(self) -> bool:
        return len(self._items) < self.capacity

    def store_item(self, item: Item) -> None:
        if not self.can_store():
            raise CryptFullError("Crypt full")
        self._items.append(item)

    def withdraw_index(self, index: int) -> Item:
        try:
            return self._items.pop(index)
        except IndexError as exc:
            raise InvalidIndexError(f"Crypt index out of range: {index}") from exc

    def list_items(self) -> List[Item]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict:
        return {"capacity": self.capacity, "items": [i.to_dict() for i in self._items]}

    @staticmethod
    def from_dict(data: dict) -> "Crypt":
        items = [Item.from_dict(raw) for raw in data.get("items", [])]
        return Crypt(capacity=int(data["capacity"]), items=items)
