from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .item import Item


@dataclass
class Inventory:
    """Simple list-based inventory.

    For this feature we only need presence/consumption behavior.
    """

    items: List[Item] = field(default_factory=list)

    def add(self, item: Item) -> None:
        self.items.append(item)

    def remove(self, item: Item) -> bool:
        """Remove the first matching item instance by value.
        Returns True if removed, False if not found.
        """
        try:
            self.items.remove(item)
            return True
        except ValueError:
            return False

    def find_first_by_id(self, item_id: str) -> Optional[Item]:
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def count_by_id(self, item_id: str) -> int:
        return sum(1 for it in self.items if it.id == item_id)

    def extend(self, items: Iterable[Item]) -> None:
        for it in items:
            self.add(it)
