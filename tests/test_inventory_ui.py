import pytest

from amor_mortuorum.core.stats import CharacterStats, Stat
from amor_mortuorum.items.model import EquipmentSlot, equipment
from amor_mortuorum.player.inventory import Equipment, Inventory
from amor_mortuorum.ui.inventory_view import InventoryViewModel
from amor_mortuorum.ui.utils import format_delta


def make_base_stats():
    return CharacterStats({
        Stat.HP: 50,
        Stat.ATK: 10,
        Stat.DEF: 5,
        Stat.SPD: 7,
        Stat.LUCK: 3,
        Stat.MAG: 0,
        Stat.RES: 0,
    })


def test_format_delta():
    assert format_delta(3) == "+3"
    assert format_delta(-2) == "-2"
    assert format_delta(0) == "0"


def test_inspect_preview_and_equip_updates_stats_immediately():
    inv = Inventory()
    eq = Equipment()
    base = make_base_stats()
    vm = InventoryViewModel(base, inv, eq)

    sword = equipment("sword_iron", "Iron Sword", EquipmentSlot.WEAPON, {Stat.ATK: 3})
    shield = equipment("shield_wood", "Wooden Shield", EquipmentSlot.OFFHAND, {Stat.DEF: 2})

    inv.add(sword)
    inv.add(shield)

    # Inspect sword should show +3 ATK delta
    insp = vm.inspect_item("sword_iron")
    deltas = {d.stat: d for d in insp.deltas}
    assert Stat.ATK in deltas
    assert deltas[Stat.ATK].delta == 3
    assert deltas[Stat.ATK].formatted() == "+3"

    # Equip sword, stats should reflect immediately
    after_equip = vm.equip("sword_iron")
    assert after_equip.current_stats["ATK"] == base[Stat.ATK] + 3

    # Now inspect shield and then equip; DEF should increase
    insp_shield = vm.inspect_item("shield_wood")
    deltas_shield = {d.stat: d for d in insp_shield.deltas}
    assert deltas_shield[Stat.DEF].delta == 2

    after_shield = vm.equip("shield_wood")
    assert after_shield.current_stats["DEF"] == base[Stat.DEF] + 2


def test_swapping_equipment_shows_negative_delta_when_replacing():
    inv = Inventory()
    eq = Equipment()
    base = make_base_stats()
    vm = InventoryViewModel(base, inv, eq)

    iron = equipment("sword_iron", "Iron Sword", EquipmentSlot.WEAPON, {Stat.ATK: 3})
    bronze = equipment("sword_bronze", "Bronze Sword", EquipmentSlot.WEAPON, {Stat.ATK: 1})

    inv.add(iron)
    inv.add(bronze)

    # Equip iron first
    vm.equip("sword_iron")
    assert vm.current_stats()[Stat.ATK] == base[Stat.ATK] + 3

    # Inspect bronze should now show -2 vs current iron
    insp = vm.inspect_item("sword_bronze")
    deltas = {d.stat: d for d in insp.deltas}
    assert deltas[Stat.ATK].delta == -2
    assert deltas[Stat.ATK].formatted() == "-2"

    # Equip bronze; stats should drop by 2
    vm.equip("sword_bronze")
    assert vm.current_stats()[Stat.ATK] == base[Stat.ATK] + 1

    # Iron should be back in inventory now
    assert inv.has("sword_iron")


def test_unequip_restores_stats_and_returns_item_to_inventory():
    inv = Inventory()
    eq = Equipment()
    base = make_base_stats()
    vm = InventoryViewModel(base, inv, eq)

    helm = equipment("helm_leather", "Leather Cap", EquipmentSlot.HEAD, {Stat.DEF: 1})

    inv.add(helm)
    vm.equip("helm_leather")
    assert vm.current_stats()[Stat.DEF] == base[Stat.DEF] + 1

    # Unequip
    res = vm.unequip(EquipmentSlot.HEAD)
    assert res.current_stats["DEF"] == base[Stat.DEF]
    assert inv.has("helm_leather")


def test_list_inventory_and_equipped_views():
    inv = Inventory()
    eq = Equipment()
    base = make_base_stats()
    vm = InventoryViewModel(base, inv, eq)

    ring = equipment("ring_cursed", "Cursed Ring", EquipmentSlot.ACCESSORY1, {Stat.ATK: 1, Stat.LUCK: -1})
    armor = equipment("armor_cloth", "Cloth Armor", EquipmentSlot.BODY, {Stat.DEF: 1})

    inv.add(ring)
    inv.add(armor)

    items = vm.list_inventory()
    ids = {i["id"] for i in items}
    assert {"ring_cursed", "armor_cloth"}.issubset(ids)

    # Equip both
    vm.equip("ring_cursed")
    vm.equip("armor_cloth")

    equipped = vm.list_equipped()
    equipped_map = {e["slot"]: e["item_id"] for e in equipped}
    assert equipped_map["ACCESSORY1"] == "ring_cursed"
    assert equipped_map["BODY"] == "armor_cloth"


def test_preview_when_slot_empty_and_when_occupied():
    inv = Inventory()
    eq = Equipment()
    base = make_base_stats()
    vm = InventoryViewModel(base, inv, eq)

    sword = equipment("sword", "Sword", EquipmentSlot.WEAPON, {Stat.ATK: 2})
    better = equipment("sword_better", "Better Sword", EquipmentSlot.WEAPON, {Stat.ATK: 5})

    inv.add(sword)
    inv.add(better)

    # Empty slot preview
    ins = vm.inspect_item("sword")
    deltas = {d.stat: d for d in ins.deltas}
    assert deltas[Stat.ATK].delta == 2

    vm.equip("sword")

    # Occupied slot preview replacing with better sword
    ins2 = vm.inspect_item("sword_better")
    deltas2 = {d.stat: d for d in ins2.deltas}
    assert deltas2[Stat.ATK].delta == 3  # 5 - 2
