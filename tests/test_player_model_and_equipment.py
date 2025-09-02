import pytest

from core.inventory import InventoryFullError
from core.stats import StatBlock
from entities.player import Player
from items.equipment import EquipmentSlot, Weapon, Armor, Helm, Shield, Accessory


def make_player():
    base = StatBlock(max_hp=30, max_mp=10, attack=5, defense=3, magic=2, speed=4)
    return Player(name="Hero", base_stats=base)


def test_equipping_items_changes_derived_stats():
    p = make_player()
    sword = Weapon(id="w1", name="Rusty Sword", bonuses=StatBlock(attack=10))
    mail = Armor(id="a1", name="Leather Mail", bonuses=StatBlock(defense=5, max_hp=5))

    # Initially base
    assert p.attack == 5
    assert p.defense == 3
    assert p.max_hp == 30

    p.equip(sword)
    assert p.attack == 15  # 5 + 10
    assert p.defense == 3

    p.equip(mail)
    assert p.defense == 8  # 3 + 5
    assert p.max_hp == 35  # 30 + 5


def test_equipping_replaces_and_moves_previous_to_inventory():
    p = make_player()
    w1 = Weapon(id="w1", name="Dagger", bonuses=StatBlock(attack=3))
    w2 = Weapon(id="w2", name="Longsword", bonuses=StatBlock(attack=8))

    # Equip first
    prev = p.equip(w1)
    assert prev is None
    assert p.attack == 5 + 3

    # Pick up second to inventory, then equip it
    p.pick_up(w2)
    assert w2 in p.inventory.items

    prev = p.equip(w2)
    # Previously equipped weapon should be moved to inventory
    assert prev is w1
    assert w1 in p.inventory.items
    # Newly equipped item removed from inventory
    assert w2 not in p.inventory.items
    assert p.attack == 5 + 8


def test_unequip_moves_item_to_inventory_and_clears_slot():
    p = make_player()
    helm = Helm(id="h1", name="Cloth Cap", bonuses=StatBlock(defense=1))

    p.equip(helm)
    assert p.equipment[EquipmentSlot.HELM] is helm

    out = p.unequip(EquipmentSlot.HELM)
    assert out is helm
    assert p.equipment[EquipmentSlot.HELM] is None
    assert helm in p.inventory.items


def test_inventory_pickup_and_capacity():
    p = Player(name="CapTest", base_stats=StatBlock(max_hp=10))

    # Reduce capacity for test
    p.inventory.capacity = 2

    acc1 = Accessory(id="acc1", name="Ring 1")
    acc2 = Accessory(id="acc2", name="Ring 2")
    acc3 = Accessory(id="acc3", name="Ring 3")

    p.pick_up(acc1)
    p.pick_up(acc2)
    assert len(p.inventory.items) == 2

    with pytest.raises(InventoryFullError):
        p.pick_up(acc3)


def test_total_stats_sum_all_slots():
    p = make_player()

    w = Weapon(id="w", name="Blade", bonuses=StatBlock(attack=7))
    a = Armor(id="a", name="Cuirass", bonuses=StatBlock(defense=6, max_hp=10))
    h = Helm(id="h", name="Helm", bonuses=StatBlock(defense=2, speed=1))
    s = Shield(id="s", name="Buckler", bonuses=StatBlock(defense=3))
    x = Accessory(id="x", name="Amulet", bonuses=StatBlock(magic=4, max_mp=5))

    p.equip(w)
    p.equip(a)
    p.equip(h)
    p.equip(s)
    p.equip(x)

    assert p.attack == 5 + 7
    assert p.defense == 3 + 6 + 2 + 3
    assert p.magic == 2 + 4
    assert p.speed == 4 + 1
    assert p.max_hp == 30 + 10
    assert p.max_mp == 10 + 5


def test_hp_mp_clamp_when_unequipping():
    # Ensure current HP/MP clamp down if max reduced by unequip
    base = StatBlock(max_hp=10, max_mp=5)
    p = Player(name="Clamp", base_stats=base)

    acc = Accessory(id="acc", name="Vital Charm", bonuses=StatBlock(max_hp=20, max_mp=5))
    p.equip(acc)

    # Heal to full
    assert p.current_hp == 30
    assert p.current_mp == 10

    # Unequip - current should clamp to new max
    p.unequip(EquipmentSlot.ACCESSORY)
    assert p.max_hp == 10
    assert p.max_mp == 5
    assert p.current_hp == 10
    assert p.current_mp == 5
