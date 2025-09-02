from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from core.inventory import Inventory, InventoryFullError
from core.stats import StatBlock
from items.base import Item
from items.equipment import Equipment, EquipmentSlot

logger = logging.getLogger(__name__)


class InvalidEquipmentSlotError(Exception):
    pass


@dataclass
class Player:
    """Player model with base stats, current resources, equipment slots, and inventory.

    Equipment slots: weapon, armor, helm, shield, accessory.
    Derived stats are computed as base stats + sum of equipment bonuses.
    """

    name: str
    base_stats: StatBlock
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Dict[EquipmentSlot, Optional[Equipment]] = field(
        default_factory=lambda: {slot: None for slot in EquipmentSlot}
    )

    current_hp: int = field(init=False)
    current_mp: int = field(init=False)

    def __post_init__(self) -> None:
        # Initialize current HP/MP to maximums
        ts = self.total_stats
        self.current_hp = ts.max_hp
        self.current_mp = ts.max_mp
        logger.debug("Initialized player %s with HP=%s MP=%s", self.name, self.current_hp, self.current_mp)

    # ---- Derived Stats ----
    @property
    def total_stats(self) -> StatBlock:
        total = self.base_stats
        for eq in self.equipment.values():
            if eq is not None:
                total = total + eq.bonuses
        return total

    @property
    def max_hp(self) -> int:
        return self.total_stats.max_hp

    @property
    def max_mp(self) -> int:
        return self.total_stats.max_mp

    @property
    def attack(self) -> int:
        return self.total_stats.attack

    @property
    def defense(self) -> int:
        return self.total_stats.defense

    @property
    def magic(self) -> int:
        return self.total_stats.magic

    @property
    def speed(self) -> int:
        return self.total_stats.speed

    # ---- Inventory ----
    def pick_up(self, item: Item) -> None:
        """Add an item to inventory.

        Raises InventoryFullError if no space.
        """
        logger.debug("%s picking up item: %s", self.name, getattr(item, "name", item))
        self.inventory.add(item)

    # ---- Equipment Management ----
    def equip(self, equipment: Equipment) -> Optional[Equipment]:
        """Equip an Equipment item into its slot.

        If the slot was already occupied, the previously equipped item is moved to inventory
        (may raise InventoryFullError if no space) and returned.

        If the new equipment exists in inventory, it is removed from inventory when equipped.
        """
        slot = equipment.slot
        if slot not in self.equipment:
            raise InvalidEquipmentSlotError(f"Unknown equipment slot: {slot}")

        previous = self.equipment[slot]

        # If equipping from inventory, remove it to avoid duplicates.
        if self.inventory.contains(equipment):
            self.inventory.remove(equipment)

        # Put the previous equipment into inventory first (maintain item availability)
        if previous is not None:
            self.inventory.add(previous)

        self.equipment[slot] = equipment
        self._clamp_current_resources_to_max()

        logger.debug(
            "%s equipped %s in slot %s (previous: %s)",
            self.name,
            equipment.name,
            slot.name,
            getattr(previous, "name", None),
        )
        return previous

    def unequip(self, slot: EquipmentSlot) -> Optional[Equipment]:
        """Unequip item from a given slot and move it to inventory.

        If the slot is empty, returns None.
        """
        if slot not in self.equipment:
            raise InvalidEquipmentSlotError(f"Unknown equipment slot: {slot}")

        item = self.equipment[slot]
        if item is None:
            return None

        # Move to inventory (may raise InventoryFullError)
        self.inventory.add(item)
        self.equipment[slot] = None
        self._clamp_current_resources_to_max()

        logger.debug("%s unequipped %s from slot %s", self.name, item.name, slot.name)
        return item

    # ---- Helpers ----
    def _clamp_current_resources_to_max(self) -> None:
        # Clamp current HP/MP after stat changes
        ts = self.total_stats
        before_hp, before_mp = self.current_hp, self.current_mp
        self.current_hp = min(self.current_hp, ts.max_hp)
        self.current_mp = min(self.current_mp, ts.max_mp)
        if (before_hp, before_mp) != (self.current_hp, self.current_mp):
            logger.debug(
                "%s current resources clamped HP: %s->%s, MP: %s->%s",
                self.name,
                before_hp,
                self.current_hp,
                before_mp,
                self.current_mp,
            )

    # Basic actions for future integration
    def heal(self, amount: int) -> int:  # pragma: no cover - convenience
        amount = max(0, amount)
        new_hp = min(self.current_hp + amount, self.max_hp)
        delta = new_hp - self.current_hp
        self.current_hp = new_hp
        return delta

    def restore_mp(self, amount: int) -> int:  # pragma: no cover - convenience
        amount = max(0, amount)
        new_mp = min(self.current_mp + amount, self.max_mp)
        delta = new_mp - self.current_mp
        self.current_mp = new_mp
        return delta
