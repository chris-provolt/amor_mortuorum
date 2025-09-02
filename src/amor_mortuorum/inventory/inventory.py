from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from amor_mortuorum.exceptions import InventoryError


@dataclass
class Inventory:
    """
    Simple stack-based inventory for consumable combat items.

    Stores item_id -> quantity.
    """

    stacks: Dict[str, int] = field(default_factory=dict)

    def add(self, item_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InventoryError("Quantity to add must be positive")
        self.stacks[item_id] = self.stacks.get(item_id, 0) + quantity

    def has(self, item_id: str, quantity: int = 1) -> bool:
        return self.stacks.get(item_id, 0) >= quantity

    def consume(self, item_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InventoryError("Quantity to consume must be positive")
        current = self.stacks.get(item_id, 0)
        if current < quantity:
            raise InventoryError(
                f"Not enough '{item_id}' to consume: have {current}, need {quantity}"
            )
        new_q = current - quantity
        if new_q == 0:
            self.stacks.pop(item_id, None)
        else:
            self.stacks[item_id] = new_q

    def quantity(self, item_id: str) -> int:
        return self.stacks.get(item_id, 0)
