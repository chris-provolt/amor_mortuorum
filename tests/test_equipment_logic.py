import pytest

from amor_mortuorum.core.stats import CharacterStats, Stat
from amor_mortuorum.items.model import EquipmentSlot, Item, ItemType, equipment
from amor_mortuorum.player.inventory import Equipment, Inventory, EquipError, InventoryError


def test_equipping_requires_item_in_inventory():
    inv = Inventory()
    eq = Equipment()
    with pytest.raises(InventoryError):
        eq.equip(inv, "missing")


def test_equipping_validation():
    inv = Inventory()
    eq = Equipment()

    # Non-equipment item
    potion = Item(id="p1", name="Potion", item_type=ItemType.CONSUMABLE, description="Heal")
    inv.add(potion)
    with pytest.raises(EquipError):
        eq.equip(inv, "p1")

    # Equipment without slot should raise on creation or equip
    with pytest.raises(ValueError):
        Item(id="bad", name="Bad", item_type=ItemType.EQUIPMENT)


def test_equipping_and_unequipping_modifiers_delta():
    inv = Inventory()
    eq = Equipment()

    helm = equipment("helm", "Helm", EquipmentSlot.HEAD, {Stat.DEF: 1, Stat.HP: 5})
    inv.add(helm)

    replaced, delta = eq.equip(inv, "helm")
    assert replaced is None
    assert delta.values[Stat.DEF] == 1
    assert delta.values[Stat.HP] == 5

    # Unequip
    removed, udelta = eq.unequip(inv, EquipmentSlot.HEAD)
    assert removed.id == "helm"
    # Unequip delta should be negative of helm stats
    assert udelta.values[Stat.DEF] == 0 - 1
    assert udelta.values[Stat.HP] == 0 - 5

    # Back in inventory
    assert inv.has("helm")
