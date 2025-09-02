from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from amor_mortuorum.core.stats import CharacterStats, Stat
from amor_mortuorum.items.model import EquipmentSlot
from amor_mortuorum.player.inventory import Equipment, Inventory
from amor_mortuorum.ui.utils import format_delta

logger = logging.getLogger(__name__)


@dataclass
class StatDelta:
    stat: Stat
    before: int
    after: int
    delta: int

    def formatted(self) -> str:
        return format_delta(self.delta)


@dataclass
class ItemInspection:
    item_id: str
    name: str
    slot: Optional[str]
    description: str
    deltas: List[StatDelta]
    current_stats: Dict[str, int]
    projected_stats: Dict[str, int]


class InventoryViewModel:
    """
    A UI-agnostic view model that exposes inventory and equipment functionality
    for listing items, inspecting them (with stat delta preview), and equipping
    or unequipping. Intended to be bound to a rendering layer (e.g., Arcade)
    but testable headlessly.
    """

    def __init__(self, base_stats: CharacterStats, inventory: Inventory, equipment: Equipment) -> None:
        self.base_stats = base_stats
        self.inventory = inventory
        self.equipment = equipment

    # ---- Query helpers ----

    def current_stats(self) -> CharacterStats:
        return self.base_stats.plus(self.equipment.total_modifiers())

    def _projected_stats_after_delta(self, delta_mods: CharacterStats) -> CharacterStats:
        # Equipment delta modifies the current equipment mods; add to base
        projected_equipment = self.equipment.total_modifiers().plus(delta_mods)
        return self.base_stats.plus(projected_equipment)

    def list_inventory(self) -> List[Dict[str, str]]:
        """Return a simple list of inventory entries for listing in the UI."""
        entries = []
        for entry in self.inventory.list_entries():
            entries.append(
                {
                    "id": entry.item.id,
                    "name": entry.item.name,
                    "type": entry.item.item_type.value,
                    "slot": entry.item.slot.value if entry.item.slot else None,
                    "quantity": str(entry.quantity),
                }
            )
        return entries

    def list_equipped(self) -> List[Dict[str, Optional[str]]]:
        return [
            {
                "slot": slot.value,
                "item_id": itm.id if itm else None,
                "name": itm.name if itm else None,
            }
            for slot, itm in self.equipment._slots.items()
        ]

    # ---- Inspect / preview ----

    def inspect_item(self, item_id: str) -> ItemInspection:
        """
        Inspect an item in inventory. For equipment, includes stat preview vs current.
        For non-equipment, deltas will be empty (or zero if needed for future use).
        """
        entry = self.inventory.get(item_id)
        item = entry.item

        current = self.current_stats()
        deltas: List[StatDelta] = []
        slot_str = item.slot.value if item.slot else None
        if item.slot is not None and item.requires_slot():
            delta_mods = self.equipment.preview_equip_delta(item)
            projected = self._projected_stats_after_delta(delta_mods)
            for stat in Stat:
                before = current[stat]
                after = projected[stat]
                if before != after:
                    deltas.append(StatDelta(stat=stat, before=before, after=after, delta=after - before))
        else:
            projected = current

        return ItemInspection(
            item_id=item.id,
            name=item.name,
            slot=slot_str,
            description=item.description,
            deltas=deltas,
            current_stats=current.to_dict(),
            projected_stats=projected.to_dict(),
        )

    # ---- Commands ----

    def equip(self, item_id: str) -> ItemInspection:
        """
        Equip an item and return an inspection including resulting deltas and new stats.
        """
        before_stats = self.current_stats()
        replaced, delta_mods = self.equipment.equip(self.inventory, item_id)
        after_stats = self.current_stats()
        entry = self.inventory._entries.get(item_id)  # May no longer exist if quantity went to 0
        item_name = None
        slot_str = None
        description = ""
        if entry is None:
            # Fetch details from the new equipment slot
            # We determine slot by searching for item_id in equipped map
            for slot, itm in self.equipment._slots.items():
                if itm and itm.id == item_id:
                    item_name = itm.name
                    slot_str = slot.value
                    description = itm.description
                    break
        else:
            item_name = entry.item.name
            slot_str = entry.item.slot.value if entry.item.slot else None
            description = entry.item.description

        deltas: List[StatDelta] = []
        for stat in Stat:
            b = before_stats[stat]
            a = after_stats[stat]
            if a != b:
                deltas.append(StatDelta(stat=stat, before=b, after=a, delta=a - b))

        return ItemInspection(
            item_id=item_id,
            name=item_name or "",
            slot=slot_str,
            description=description,
            deltas=deltas,
            current_stats=after_stats.to_dict(),
            projected_stats=after_stats.to_dict(),
        )

    def unequip(self, slot: EquipmentSlot) -> ItemInspection:
        """
        Unequip the item in the given slot and return an inspection reflecting
        the change. If nothing is equipped, returns no deltas.
        """
        before = self.current_stats()
        removed, _delta = self.equipment.unequip(self.inventory, slot)
        after = self.current_stats()

        deltas: List[StatDelta] = []
        for stat in Stat:
            b = before[stat]
            a = after[stat]
            if a != b:
                deltas.append(StatDelta(stat=stat, before=b, after=a, delta=a - b))

        name = removed.name if removed else ""
        item_id = removed.id if removed else ""
        description = removed.description if removed else ""

        return ItemInspection(
            item_id=item_id,
            name=name,
            slot=slot.value,
            description=description,
            deltas=deltas,
            current_stats=after.to_dict(),
            projected_stats=after.to_dict(),
        )
