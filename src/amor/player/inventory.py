from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from amor.items.models import Item

logger = logging.getLogger(__name__)


@dataclass
class Inventory:
    """
    A simple inventory model with optional capacity.
    """

    capacity: int | None = None
    items: List[Item] = field(default_factory=list)

    def add(self, item: Item) -> bool:
        if self.capacity is not None and len(self.items) >= self.capacity:
            logger.warning("Inventory full: cannot add item %s", item.id)
            return False
        self.items.append(item)
        logger.debug("Added item %s to inventory", item.id)
        return True

    def __len__(self) -> int:
        return len(self.items)


__all__ = ["Inventory"]
