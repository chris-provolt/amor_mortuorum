from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from .errors import InvalidOperation, NotFound
from .config import DEFAULT_ITEMS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    type: str
    stackable: bool = True
    max_stack: int = 99
    meta: bool = False


class ItemCatalog:
    """Item catalog provides lookups by item id.

    In a full game, this would be built from data files. Here we ship with
    sensible defaults that can be extended.
    """

    def __init__(self, items: Optional[Dict[str, Dict]] = None):
        if items is None:
            items = DEFAULT_ITEMS
        self._items: Dict[str, Item] = {
            iid: Item(**data) for iid, data in items.items()
        }

    def get(self, item_id: str) -> Item:
        try:
            return self._items[item_id]
        except KeyError as e:
            raise NotFound(f"Unknown item id: {item_id}") from e

    def has(self, item_id: str) -> bool:
        return item_id in self._items


@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict)

    def count(self, item_id: str) -> int:
        return self.items.get(item_id, 0)

    def add(self, item: Item, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Quantity to add must be positive")
        current = self.items.get(item.id, 0)
        new_total = current + quantity
        if item.stackable and new_total > item.max_stack:
            raise InvalidOperation(
                f"Exceeds max stack for {item.name}: {new_total} > {item.max_stack}"
            )
        self.items[item.id] = new_total

    def remove(self, item: Item, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Quantity to remove must be positive")
        current = self.items.get(item.id, 0)
        if current < quantity:
            raise InvalidOperation(
                f"Cannot remove {quantity}x {item.name}; only {current} in inventory"
            )
        remaining = current - quantity
        if remaining == 0:
            self.items.pop(item.id, None)
        else:
            self.items[item.id] = remaining


@dataclass
class Player:
    name: str = "Wanderer"
    max_hp: int = 100
    hp: int = 100
    gold: int = 100
    inventory: Inventory = field(default_factory=Inventory)

    def heal_full(self) -> None:
        logger.debug("Healing player to full HP: %s -> %s", self.hp, self.max_hp)
        self.hp = self.max_hp

    def spend_gold(self, amount: int) -> None:
        if amount < 0:
            raise InvalidOperation("Cannot spend negative gold")
        if self.gold < amount:
            from .errors import InsufficientGold

            raise InsufficientGold(
                f"Insufficient gold: have {self.gold}, need {amount}"
            )
        logger.debug("Spending gold: %s - %s", self.gold, amount)
        self.gold -= amount

    def add_gold(self, amount: int) -> None:
        if amount < 0:
            raise InvalidOperation("Cannot add negative gold")
        logger.debug("Adding gold: %s + %s", self.gold, amount)
        self.gold += amount
