from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from .errors import CryptFull, InvalidOperation, NotFound
from .models import ItemCatalog, Player
from .save import SaveData, CryptSlot

logger = logging.getLogger(__name__)


@dataclass
class CryptConfig:
    slots: int = 3


class Crypt:
    """Persistent item storage across runs.

    Up to 3 slots, each slot holds a stack of a single item id.
    """

    def __init__(self, save: SaveData, catalog: ItemCatalog | None = None, config: CryptConfig | None = None):
        self.save = save
        self.catalog = catalog or ItemCatalog()
        self.config = config or CryptConfig()
        # Normalize crypt slots (enforce positive quantities)
        self.save.crypt = [s for s in self.save.crypt if s.quantity > 0][: self.config.slots]

    def list_slots(self) -> List[CryptSlot]:
        return list(self.save.crypt)

    def deposit(self, player: Player, item_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Deposit quantity must be positive")
        item = self.catalog.get(item_id)
        # Validate player has enough to deposit
        if player.inventory.count(item.id) < quantity:
            raise InvalidOperation(
                f"Player lacks {quantity}x {item.name} to deposit"
            )
        # If item exists in any slot, stack it; else use new slot
        for slot in self.save.crypt:
            if slot.item_id == item.id:
                slot.quantity += quantity
                player.inventory.remove(item, quantity)
                logger.debug("Deposited %s into existing crypt slot: %s", quantity, slot)
                return
        # Need a new slot
        if len(self.save.crypt) >= self.config.slots:
            raise CryptFull("Crypt is full (3 slots)")
        self.save.crypt.append(CryptSlot(item_id=item.id, quantity=quantity))
        player.inventory.remove(item, quantity)
        logger.debug("Deposited %s of %s into new crypt slot", quantity, item.id)

    def withdraw(self, player: Player, slot_index: int, quantity: Optional[int] = None) -> None:
        if not (0 <= slot_index < len(self.save.crypt)):
            raise NotFound(f"Crypt slot index out of range: {slot_index}")
        slot = self.save.crypt[slot_index]
        item = self.catalog.get(slot.item_id)
        if quantity is None:
            quantity = slot.quantity
        if quantity <= 0:
            raise InvalidOperation("Withdraw quantity must be positive")
        if quantity > slot.quantity:
            raise InvalidOperation(
                f"Cannot withdraw {quantity}; slot has only {slot.quantity}"
            )
        # Add to player inventory (may raise due to stack limits)
        player.inventory.add(item, quantity)
        slot.quantity -= quantity
        if slot.quantity == 0:
            # Remove empty slot to free capacity
            self.save.crypt.pop(slot_index)
        logger.debug(
            "Withdrew %s of %s from crypt slot %s; remaining: %s",
            quantity,
            item.id,
            slot_index,
            slot.quantity if slot_index < len(self.save.crypt) else 0,
        )
