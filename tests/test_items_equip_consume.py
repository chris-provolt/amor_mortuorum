import pytest

from amor_mortuorum.characters.stats import Stats
from amor_mortuorum.inventory.inventory import Inventory
from amor_mortuorum.items.models import EquipmentSlot, Item, ItemType


def test_equip_applies_and_replaces_stat_deltas():
    stats = Stats(
        base_max_hp=100, base_max_mp=20, base_atk=10, base_defense=5,
        base_magic=3, base_resistance=2, base_speed=4, base_luck=1
    )

    inv = Inventory()

    sword_1 = Item.from_dict({
        'id': 'iron_sword', 'name': 'Iron Sword', 'type': 'equipment',
        'slot': 'weapon', 'stat_deltas': {'atk': 5}
    })
    sword_2 = Item.from_dict({
        'id': 'steel_sword', 'name': 'Steel Sword', 'type': 'equipment',
        'slot': 'weapon', 'stat_deltas': {'atk': 10}
    })

    inv.add_item(sword_1, 1)
    inv.add_item(sword_2, 1)

    # Equip iron sword
    prev = inv.equip(stats, 'iron_sword')
    assert prev is None
    assert stats.atk == 15
    assert inv.equipped()[EquipmentSlot.WEAPON] == 'iron_sword'

    # Replace with steel sword
    prev = inv.equip(stats, 'steel_sword')
    assert prev == 'iron_sword'
    assert stats.atk == 20  # 10 base + 10 steel
    assert inv.equipped()[EquipmentSlot.WEAPON] == 'steel_sword'

    # Unequip
    removed = inv.unequip(stats, EquipmentSlot.WEAPON)
    assert removed == 'steel_sword'
    assert stats.atk == 10
    assert inv.equipped()[EquipmentSlot.WEAPON] is None


def test_consume_potion_heals_and_is_removed():
    stats = Stats(base_max_hp=100, base_max_mp=20, base_atk=5, base_defense=5)
    stats.hp = 40

    inv = Inventory()

    potion = Item.from_dict({
        'id': 'potion_small', 'name': 'Small Potion', 'type': 'consumable',
        'effects': [{ 'type': 'heal_hp', 'amount': 50 }]
    })

    inv.add_item(potion, 1)
    summary = inv.consume(stats, 'potion_small')

    assert summary['heal_hp'] == 50
    assert stats.hp == 90
    # Item should be removed from inventory
    assert inv.get_quantity('potion_small') == 0


def test_consume_scroll_mp_percent_and_quantity_decrements():
    stats = Stats(base_max_hp=80, base_max_mp=50, base_atk=5, base_defense=5)
    stats.mp = 10

    inv = Inventory()

    scroll = Item.from_dict({
        'id': 'ether_scroll', 'name': 'Ether Scroll', 'type': 'consumable',
        'effects': [{ 'type': 'heal_mp', 'amount': { 'percent_max': 0.5 } }]
    })

    inv.add_item(scroll, 2)

    summary = inv.consume(stats, 'ether_scroll')
    assert summary['heal_mp'] == 25  # 50% of 50
    assert stats.mp == 35
    assert inv.get_quantity('ether_scroll') == 1

    # Consume again should clamp to max
    summary = inv.consume(stats, 'ether_scroll')
    # Expected heal is 15 (to reach 50)
    assert summary['heal_mp'] == 15
    assert stats.mp == 50
    assert inv.get_quantity('ether_scroll') == 0


def test_invalid_operations_raise():
    stats = Stats()
    inv = Inventory()

    # Non-existent item
    with pytest.raises(ValueError):
        inv.equip(stats, 'nope')

    # Wrong type for consume/equip
    key_item = Item.from_dict({'id': 'key1', 'name': 'Crypt Key', 'type': 'key'})
    inv.add_item(key_item, 1)
    with pytest.raises(ValueError):
        inv.consume(stats, 'key1')

    armor = Item.from_dict({
        'id': 'leather_armor', 'name': 'Leather Armor', 'type': 'equipment',
        'slot': 'armor', 'stat_deltas': {'defense': 2}
    })
    inv.add_item(armor, 1)
    # Equip armor (valid)
    inv.equip(stats, 'leather_armor')
    # Try to consume it
    with pytest.raises(ValueError):
        inv.consume(stats, 'leather_armor')
