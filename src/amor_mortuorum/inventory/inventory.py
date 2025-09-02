from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from ..characters.stats import Stats
from ..items.models import EquipmentSlot, Item, ItemType, apply_consumable_effects

logger = logging.getLogger(__name__)


@dataclass
class InventoryEntry:
    item: Item
    qty: int


class Inventory:
    """
    Inventory with item quantities and equipped items per slot.

    - Equipment: equipping applies stat deltas to the provided Stats instance.
    - Consumables: consuming applies effects and reduces quantity (removing item at zero).

    Note: Equipping does not consume inventory quantity; it only changes the equipped mapping.
    """

    def __init__(self) -> None:
        self._items: Dict[str, InventoryEntry] = {}
        self._equipped: Dict[EquipmentSlot, Optional[str]] = {
            EquipmentSlot.WEAPON: None,
            EquipmentSlot.ARMOR: None,
            EquipmentSlot.ACCESSORY: None,
        }

    def add_item(self, item: Item, qty: int = 1) -> None:
        if qty <= 0:
            return
        entry = self._items.get(item.id)
        if entry:
            entry.qty += qty
        else:
            self._items[item.id] = InventoryEntry(item=item, qty=qty)
        logger.debug('Added %d x %s (total=%d)', qty, item.id, self._items[item.id].qty)

    def get_quantity(self, item_id: str) -> int:
        entry = self._items.get(item_id)
        return entry.qty if entry else 0

    def get_item(self, item_id: str) -> Optional[Item]:
        entry = self._items.get(item_id)
        return entry.item if entry else None

    def equipped(self) -> Dict[EquipmentSlot, Optional[str]]:
        return dict(self._equipped)

    def equip(self, stats: Stats, item_id: str) -> Optional[str]:
        """
        Equip the given item, applying its stat deltas.

        Returns the previously equipped item id in that slot (if any).
        Raises ValueError for invalid operations.
        """
        entry = self._items.get(item_id)
        if not entry:
            raise ValueError(f'Item not in inventory: {item_id}')
        item = entry.item
        if item.type != ItemType.EQUIPMENT:
            raise ValueError(f'Cannot equip non-equipment item: {item_id}')
        slot = item.slot
        assert slot is not None

        # Unequip previous in slot if present
        previous_id = self._equipped.get(slot)
        if previous_id:
            prev_item = self._items[previous_id].item
            stats.remove_stat_deltas(prev_item.stat_deltas)
            logger.debug('Unequipped %s from %s', previous_id, slot)

        # Equip new
        self._equipped[slot] = item_id
        stats.apply_stat_deltas(item.stat_deltas)
        logger.debug('Equipped %s to %s; applied deltas %s', item_id, slot, item.stat_deltas)
        return previous_id

    def unequip(self, stats: Stats, slot: EquipmentSlot) -> Optional[str]:
        """
        Unequip currently equipped item from the slot and remove its stat deltas.

        Returns the unequipped item id if any.
        """
        item_id = self._equipped.get(slot)
        if not item_id:
            return None
        prev_item = self._items[item_id].item
        stats.remove_stat_deltas(prev_item.stat_deltas)
        self._equipped[slot] = None
        logger.debug('Unequipped %s from %s; removed deltas %s', item_id, slot, prev_item.stat_deltas)
        return item_id

    def consume(self, stats: Stats, item_id: str) -> Dict[str, int]:
        """
        Consume one quantity of a consumable item, applying its effects to stats.

        Returns a summary of applied effects. Removes the item from inventory when qty reaches zero.
        Raises ValueError for invalid operations.
        """
        entry = self._items.get(item_id)
        if not entry:
            raise ValueError(f'Item not in inventory: {item_id}')
        if entry.item.type != ItemType.CONSUMABLE:
            raise ValueError(f'Cannot consume non-consumable item: {item_id}')
        # Apply effects
        summary = apply_consumable_effects(stats, entry.item.effects)
        # Reduce quantity
        entry.qty -= 1
        if entry.qty <= 0:
            del self._items[item_id]
            logger.debug('Consumed last %s; removed from inventory', item_id)
        else:
            logger.debug('Consumed %s; remaining=%d', item_id, entry.qty)
        return summary
