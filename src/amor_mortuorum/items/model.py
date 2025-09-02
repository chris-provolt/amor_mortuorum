from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from amor_mortuorum.core.stats import CharacterStats, Stat

logger = logging.getLogger(__name__)


class ItemType(Enum):
    EQUIPMENT = "EQUIPMENT"
    CONSUMABLE = "CONSUMABLE"
    QUEST = "QUEST"


class EquipmentSlot(Enum):
    WEAPON = "WEAPON"
    OFFHAND = "OFFHAND"  # shield, secondary weapon
    HEAD = "HEAD"
    BODY = "BODY"
    ACCESSORY1 = "ACCESSORY1"
    ACCESSORY2 = "ACCESSORY2"


@dataclass(frozen=True)
class Item:
    """
    Immutable item definition. Equipment items include a slot and stat modifiers.
    """

    id: str
    name: str
    item_type: ItemType
    description: str = ""
    slot: Optional[EquipmentSlot] = None
    modifiers: CharacterStats = CharacterStats()
    stackable: bool = False

    def requires_slot(self) -> bool:
        return self.item_type == ItemType.EQUIPMENT

    def ensure_valid(self) -> None:
        if self.item_type == ItemType.EQUIPMENT and self.slot is None:
            raise ValueError(f"Equipment item {self.id} missing slot")
        if self.item_type != ItemType.EQUIPMENT and self.slot is not None:
            raise ValueError(f"Non-equipment item {self.id} should not have a slot")


# Convenience helpers to build equipment items with a simple dict of modifiers.

def equipment(
    id: str,
    name: str,
    slot: EquipmentSlot,
    modifiers: Dict[Stat, int],
    description: str = "",
) -> Item:
    itm = Item(
        id=id,
        name=name,
        item_type=ItemType.EQUIPMENT,
        slot=slot,
        modifiers=CharacterStats(modifiers),
        description=description,
        stackable=False,
    )
    itm.ensure_valid()
    return itm
