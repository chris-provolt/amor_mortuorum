import pytest

from amormortuorum.data import GameData
from amormortuorum.errors import InsufficientGold, InvalidOperation
from amormortuorum.systems.entities import Enemy, Inventory, Player, new_player


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_inventory_stacks_and_limits(data):
    inv = Inventory()
    potion = data.item("potion_small")
    inv.add(potion, 3)
    assert inv.count("potion_small") == 3
    inv.remove(potion, 2)
    assert inv.count("potion_small") == 1
    inv.remove(potion, 1)
    assert "potion_small" not in inv.items
    with pytest.raises(InvalidOperation):
        inv.remove(potion, 1)
    blade = data.item("blade_bone")
    inv.add(blade, 1)
    with pytest.raises(InvalidOperation):
        inv.add(blade, 1)  # non-stackable
    with pytest.raises(InvalidOperation):
        inv.add(potion, 0)


def test_equipment_bonus_and_swap(data):
    p = new_player()
    base_atk = p.effective_atk(data)
    p.inventory.add(data.item("dagger_rust"), 1)
    p.inventory.add(data.item("blade_bone"), 1)

    assert p.equip_from_inventory(data.item("dagger_rust"), data) is None
    assert p.effective_atk(data) == base_atk + 1
    assert p.inventory.count("dagger_rust") == 0

    replaced = p.equip_from_inventory(data.item("blade_bone"), data)
    assert replaced == "dagger_rust"
    assert p.effective_atk(data) == base_atk + 3
    assert p.inventory.count("dagger_rust") == 1  # went back to the bag

    with pytest.raises(InvalidOperation):
        p.equipment.equip(data.item("potion_small"))


def test_heal_damage_and_gold():
    p = new_player()
    p.take_damage(10)
    assert p.hp == p.max_hp - 10
    assert p.heal(4) == 4
    assert p.heal(1000) == 6
    assert p.hp == p.max_hp
    assert p.take_damage(1000) == p.max_hp
    assert not p.is_alive
    p.heal_full()
    assert p.is_alive and p.stats.mp == p.stats.max_mp

    p.gold = 10
    p.spend_gold(4)
    assert p.gold == 6
    with pytest.raises(InsufficientGold):
        p.spend_gold(7)
    with pytest.raises(InvalidOperation):
        p.add_gold(-1)


def test_player_round_trips_through_dict(data):
    p = new_player("Ash")
    p.inventory.add(data.item("potion_small"), 2)
    p.inventory.add(data.item("blade_bone"), 1)
    p.equip_from_inventory(data.item("blade_bone"), data)
    p.take_damage(5)
    p.xp, p.level, p.gold = 12, 2, 77

    clone = Player.from_dict(p.to_dict())
    assert clone.to_dict() == p.to_dict()
    assert clone.effective_atk(data) == p.effective_atk(data)
    assert clone.hp == p.hp and clone.name == "Ash"


def test_enemy_from_def(data):
    e = Enemy.from_def(data.enemy("bone_guard"))
    assert e.name == "Bone Guard" and e.stats.hp == 20 and e.stats.df == 5
    assert e.take_damage(25) == 20
    assert not e.is_alive
