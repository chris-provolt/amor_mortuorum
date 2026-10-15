from random import Random

import pytest

from amormortuorum.data import DataError, GameData
from amormortuorum.errors import InsufficientGold, InvalidOperation
from amormortuorum.persistence import RunState
from amormortuorum.systems.combat import Action, ActionKind, Battle
from amormortuorum.systems.entities import Enemy, Player
from amormortuorum.systems.party import (
    MAX_PARTY,
    available_companions,
    dismiss,
    most_wounded,
    recruit,
)
from amormortuorum.systems.progression import grant_xp
from amormortuorum.systems.run import Run, new_run


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_companions_load(data):
    assert len(data.companions) == 4
    vel = data.companion("sister_vel")
    assert vel.cost == 80 and vel.stats["max_mp"] == 16
    with pytest.raises(DataError):
        data.companion("nobody")


def test_recruit_costs_gold_matches_level_and_caps_party(data):
    run = new_run(data, seed=1)
    grant_xp(run.leader, data.xp_curve.xp_for_level(3), data)
    run.leader.gold = 1000
    assert len(available_companions(run, data)) == 4

    member = recruit(run, "ossian", data)
    assert member in run.party and len(run.party) == 2
    assert member.level == 3 and member.companion_id == "ossian"
    assert member.hp == member.max_hp and member.max_hp > 55  # levelled up from the template
    assert run.leader.gold == 1000 - 60
    assert len(available_companions(run, data)) == 3

    with pytest.raises(InvalidOperation, match="already"):
        recruit(run, "ossian", data)
    recruit(run, "sister_vel", data)
    recruit(run, "pale_cassia", data)
    assert len(run.party) == MAX_PARTY
    with pytest.raises(InvalidOperation, match="full"):
        recruit(run, "brother_moss", data)

    gone = dismiss(run, 1)
    assert gone.companion_id == "ossian" and len(run.party) == 3
    with pytest.raises(InvalidOperation):
        dismiss(run, 0)


def test_recruit_needs_gold(data):
    run = new_run(data, seed=1)
    run.leader.gold = 10
    with pytest.raises(InsufficientGold):
        recruit(run, "ossian", data)
    assert len(run.party) == 1


def test_party_round_trips_through_run_state(data):
    run = new_run(data, seed=4)
    run.leader.gold = 500
    recruit(run, "brother_moss", data)
    run.party[1].inventory.add(data.item("blade_bone"), 1)
    run.party[1].equip_from_inventory(data.item("blade_bone"), data)
    clone = Run.from_run_state(RunState.from_dict(run.to_run_state().to_dict()))
    assert [m.name for m in clone.party] == ["Wanderer", "Brother Moss"]
    assert clone.party[1].companion_id == "brother_moss"
    assert clone.party[1].equipment.slots["weapon"] == "blade_bone"


def test_combat_uses_shared_bag_and_rewards_every_survivor(data):
    run = new_run(data, seed=2)
    run.leader.gold = 500
    recruit(run, "sister_vel", data)
    leader, vel = run.party
    vel.inventory.items.clear()
    bag = leader.inventory
    bag.add(data.item("potion_small"), 1)
    potions = bag.count("potion_small")
    vel.take_damage(10)

    foe = Enemy.from_def(data.enemy("skel_basic"))
    battle = Battle(run.party, [foe], Random(5), data)
    assert battle.bag is bag
    # Vel (index 1) uses a potion from the shared bag on herself
    assert battle.submit(Action(ActionKind.ITEM, 1, target=1, item_id="potion_small")) == []
    events = battle.submit(Action(ActionKind.ATTACK, 0))
    assert any("Sister Vel uses Grave-Touched Draught" in e.text for e in events)
    assert bag.count("potion_small") == potions - 1

    foe.stats.hp = 0  # end it
    battle._update_outcome()
    xp_l, xp_v = leader.xp, vel.xp
    xp, gold = battle.apply_rewards()
    assert leader.xp == xp_l + xp and vel.xp == xp_v + xp
    assert leader.gold == 500 - 80 + gold and vel.gold == 0


def test_most_wounded_picks_lowest_fraction():
    a = Player(name="a")
    b = Player(name="b")
    c = Player(name="c")
    b.take_damage(20)
    c.take_damage(1000)
    assert most_wounded([a, b, c]) == 1
    assert most_wounded([c]) is None
