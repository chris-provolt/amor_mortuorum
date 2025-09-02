from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from core.stats import StatBlock
from items.base import Item


class EquipmentSlot(Enum):
    WEAPON = auto()
    ARMOR = auto()
    HELM = auto()
    SHIELD = auto()
    ACCESSORY = auto()


@dataclass
class Equipment(Item):
    """Equipment item that can be equipped in a specific slot and grants stat bonuses."""

    slot: EquipmentSlot
    bonuses: StatBlock = StatBlock.zeros()

    def __post_init__(self) -> None:
        # Basic validation
        if not isinstance(self.slot, EquipmentSlot):
            raise TypeError("slot must be an EquipmentSlot")
        # Ensure bonuses is StatBlock
        if not isinstance(self.bonuses, StatBlock):
            raise TypeError("bonuses must be a StatBlock")


# Convenience subclasses (type markers)
@dataclass
class Weapon(Equipment):
    def __init__(self, id: str, name: str, description: str = "", bonuses: Optional[StatBlock] = None):
        super().__init__(id=id, name=name, description=description, slot=EquipmentSlot.WEAPON, bonuses=bonuses or StatBlock.zeros())


@dataclass
class Armor(Equipment):
    def __init__(self, id: str, name: str, description: str = "", bonuses: Optional[StatBlock] = None):
        super().__init__(id=id, name=name, description=description, slot=EquipmentSlot.ARMOR, bonuses=bonuses or StatBlock.zeros())


@dataclass
class Helm(Equipment):
    def __init__(self, id: str, name: str, description: str = "", bonuses: Optional[StatBlock] = None):
        super().__init__(id=id, name=name, description=description, slot=EquipmentSlot.HELM, bonuses=bonuses or StatBlock.zeros())


@dataclass
class Shield(Equipment):
    def __init__(self, id: str, name: str, description: str = "", bonuses: Optional[StatBlock] = None):
        super().__init__(id=id, name=name, description=description, slot=EquipmentSlot.SHIELD, bonuses=bonuses or StatBlock.zeros())


@dataclass
class Accessory(Equipment):
    def __init__(self, id: str, name: str, description: str = "", bonuses: Optional[StatBlock] = None):
        super().__init__(id=id, name=name, description=description, slot=EquipmentSlot.ACCESSORY, bonuses=bonuses or StatBlock.zeros())
