"""Crypt service: moves item stacks between a player's bag and the persistent Crypt."""
from __future__ import annotations

import logging
from typing import List, Optional

from ..data import GameData
from ..errors import CryptFull, InvalidOperation, NotFound
from ..persistence import Crypt, Item
from .entities import Player

logger = logging.getLogger(__name__)


class CryptService:
    """Up to ``Crypt.MAX_SLOTS`` slots; each slot holds one stack of a single item id."""

    def __init__(self, crypt: Crypt, data: GameData) -> None:
        self.crypt = crypt
        self.data = data
        # Drop empty or unknown stacks defensively (old saves, edited files)
        self.crypt.items = [
            it for it in self.crypt.items if it.qty > 0 and self.data.has_item(it.id)
        ][: self.crypt.MAX_SLOTS]

    @property
    def capacity(self) -> int:
        return self.crypt.MAX_SLOTS

    def list_slots(self) -> List[Item]:
        return list(self.crypt.items)

    def is_full(self) -> bool:
        return len(self.crypt.items) >= self.capacity

    def _slot_for(self, item_id: str) -> Optional[Item]:
        for slot in self.crypt.items:
            if slot.id == item_id:
                return slot
        return None

    def deposit(self, player: Player, item_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Deposit quantity must be positive")
        if not self.data.has_item(item_id):
            raise NotFound(f"Unknown item id: {item_id}")
        item = self.data.item(item_id)
        if player.inventory.count(item.id) < quantity:
            raise InvalidOperation(f"Player lacks {quantity}x {item.name} to deposit")
        slot = self._slot_for(item.id)
        if slot is None:
            if self.is_full():
                raise CryptFull(f"Crypt is full ({self.capacity} slots)")
            player.inventory.remove(item, quantity)
            self.crypt.add_item(Item(id=item.id, name=item.name, qty=quantity))
        else:
            player.inventory.remove(item, quantity)
            slot.qty += quantity
        logger.debug("Deposited %sx %s into crypt", quantity, item.id)

    def withdraw(self, player: Player, slot_index: int, quantity: Optional[int] = None) -> None:
        if not (0 <= slot_index < len(self.crypt.items)):
            raise NotFound(f"Crypt slot index out of range: {slot_index}")
        slot = self.crypt.items[slot_index]
        item = self.data.item(slot.id)
        if quantity is None:
            quantity = slot.qty
        if quantity <= 0:
            raise InvalidOperation("Withdraw quantity must be positive")
        if quantity > slot.qty:
            raise InvalidOperation(f"Cannot withdraw {quantity}; slot has only {slot.qty}")
        player.inventory.add(item, quantity)  # may raise on stack limits
        slot.qty -= quantity
        if slot.qty == 0:
            self.crypt.remove_item(slot_index)
        logger.debug("Withdrew %sx %s from crypt slot %s", quantity, item.id, slot_index)
