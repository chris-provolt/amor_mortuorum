from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from amor_mortuorum.core.stats import CharacterStats, Stat
from amor_mortuorum.items.model import EquipmentSlot, Item, ItemType

logger = logging.getLogger(__name__)


class InventoryError(Exception):
    pass


class EquipError(Exception):
    pass


@dataclass
class InventoryEntry:
    item: Item
    quantity: int = 1

    def add(self, qty: int = 1) -> None:
        self.quantity += qty

    def remove(self, qty: int = 1) -> None:
        if qty > self.quantity:
            raise InventoryError("Attempted to remove more items than available")
        self.quantity -= qty


class Inventory:
    """
    Simple inventory with stackable and non-stackable items.

    Equipment items are non-stackable by default and when equipped are removed
    from the inventory and tracked by Equipment (so they don't appear twice).
    """

    def __init__(self) -> None:
        self._entries: Dict[str, InventoryEntry] = {}

    def add(self, item: Item, qty: int = 1) -> None:
        if qty <= 0:
            return
        entry = self._entries.get(item.id)
        if entry is None:
            if qty > 1 and not item.stackable:
                # Store as multiple entries each with 1 quantity for non-stackables
                # but we still key by id; instead, we simulate stacks with count = qty
                # Non-stackables are tracked as count for simplicity here.
                self._entries[item.id] = InventoryEntry(item=item, quantity=qty)
            else:
                self._entries[item.id] = InventoryEntry(item=item, quantity=qty)
        else:
            if not entry.item.stackable and entry.quantity > 0:
                # Non-stackable but we treat quantity as count of identical uniques.
                entry.add(qty)
            else:
                entry.add(qty)

    def remove(self, item_id: str, qty: int = 1) -> None:
        entry = self._entries.get(item_id)
        if entry is None or entry.quantity < qty:
            raise InventoryError(f"Item {item_id} not found or insufficient quantity")
        entry.remove(qty)
        if entry.quantity == 0:
            del self._entries[item_id]

    def get(self, item_id: str) -> InventoryEntry:
        entry = self._entries.get(item_id)
        if entry is None:
            raise InventoryError(f"Item {item_id} not in inventory")
        return entry

    def list_entries(self) -> List[InventoryEntry]:
        return list(self._entries.values())

    def has(self, item_id: str) -> bool:
        return item_id in self._entries and self._entries[item_id].quantity > 0


class Equipment:
    """
    Tracks currently equipped items across standard slots. Computes total
    stat modifiers and applies equip/unequip operations with validation.
    """

    def __init__(self) -> None:
        self._slots: Dict[EquipmentSlot, Optional[Item]] = {
            EquipmentSlot.WEAPON: None,
            EquipmentSlot.OFFHAND: None,
            EquipmentSlot.HEAD: None,
            EquipmentSlot.BODY: None,
            EquipmentSlot.ACCESSORY1: None,
            EquipmentSlot.ACCESSORY2: None,
        }

    def get(self, slot: EquipmentSlot) -> Optional[Item]:
        return self._slots.get(slot)

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {slot.value: (itm.id if itm else None) for slot, itm in self._slots.items()}

    def total_modifiers(self) -> CharacterStats:
        mods = [itm.modifiers for itm in self._slots.values() if itm is not None]
        return CharacterStats.sum(mods)

    def preview_equip_delta(self, item: Item) -> CharacterStats:
        """
        Compute the change in equipment modifiers if this item were equipped,
        including replacing any currently equipped item in that slot.
        """
        if item.item_type != ItemType.EQUIPMENT or item.slot is None:
            raise EquipError("Can only preview equipping an equipment item with a slot")
        current = self.get(item.slot)
        current_mods = current.modifiers if current else CharacterStats()
        return item.modifiers.minus(current_mods)

    def equip(self, inventory: Inventory, item_id: str) -> Tuple[Optional[Item], CharacterStats]:
        """
        Equip an item from inventory. Returns (replaced_item, delta_modifiers).

        The delta_modifiers represent the change in total equipment modifiers.
        """
        entry = inventory.get(item_id)
        item = entry.item
        if item.item_type != ItemType.EQUIPMENT or item.slot is None:
            raise EquipError("Item is not equippable or has no slot")

        slot = item.slot
        replaced = self._slots.get(slot)
        try:
            # Remove the new item from inventory first (atomic via try/except)
            inventory.remove(item_id, 1)
            # Place the new item in the slot
            self._slots[slot] = item
            # Add the replaced one back to inventory (if any)
            if replaced is not None:
                inventory.add(replaced, 1)
        except Exception:
            # Rollback slot on failure
            self._slots[slot] = replaced
            logger.exception("Failed to equip item; rolled back state")
            raise

        current_mods = replaced.modifiers if replaced else CharacterStats()
        delta = item.modifiers.minus(current_mods)
        return replaced, delta

    def unequip(self, inventory: Inventory, slot: EquipmentSlot) -> Tuple[Optional[Item], CharacterStats]:
        """
        Unequip an item from a slot, placing it into inventory.
        Returns (removed_item, delta_modifiers) where delta is negative of removed mods.
        """
        current = self._slots.get(slot)
        if current is None:
            return None, CharacterStats()  # no-op
        # Remove from slot and add to inventory
        self._slots[slot] = None
        inventory.add(current, 1)
        delta = CharacterStats().minus(current.modifiers)  # negative of current
        return current, delta
