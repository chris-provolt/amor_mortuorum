import pytest

from amormortuorum.data import MAX_FLOOR, GameData
from amormortuorum.persistence import MetaState, RunState
from amormortuorum.systems.run import RESURRECTION_TOKEN_ID, Run, new_run


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_new_run_has_starting_kit_and_floor_one(data):
    run = new_run(data, seed=123, name="Ash")
    assert run.floor == 1 and run.seed == 123
    assert run.leader.name == "Ash"
    assert run.leader.inventory.count("potion_small") == 2
    assert run.has_token()
    assert run.alive and run.in_graveyard


def test_descend_caps_at_max_floor(data):
    run = new_run(data, seed=1)
    run.steps_since_encounter = 9
    run.leader.take_damage(20)
    run.leader.stats.mp = 0
    assert run.descend() == 2
    assert run.steps_since_encounter == 0
    assert run.leader.hp == run.leader.max_hp - 20 + run.leader.max_hp * 10 // 100
    assert run.leader.stats.mp == max(1, run.leader.stats.max_mp * 15 // 100)
    run.floor = MAX_FLOOR
    assert run.descend() == MAX_FLOOR


def test_round_trip_through_run_state(data):
    run = new_run(data, seed=99)
    run.floor = 7
    run.steps_since_encounter = 3
    run.in_graveyard = False
    run.leader.take_damage(9)
    state = run.to_run_state()
    assert isinstance(state, RunState)
    assert state.floor == 7 and state.rng_seed == 99 and state.in_graveyard is False
    clone = Run.from_run_state(RunState.from_dict(state.to_dict()))
    assert clone.floor == 7 and clone.seed == 99 and clone.steps_since_encounter == 3
    assert clone.leader.hp == run.leader.hp
    assert clone.leader.inventory.to_dict() == run.leader.inventory.to_dict()


def test_death_with_token_revives_and_consumes_it(data):
    run = new_run(data, seed=5)
    run.floor = 12
    run.in_graveyard = False
    run.leader.take_damage(1000)
    meta = MetaState()
    result = run.on_death(meta, data)
    assert result.revived is True
    assert run.leader.inventory.count(RESURRECTION_TOKEN_ID) == 0
    assert run.leader.hp == 1 and run.alive
    assert run.in_graveyard is True
    assert meta.deepest_floor == 12


def test_death_without_token_ends_run(data):
    run = new_run(data, seed=5)
    run.leader.inventory.remove(data.item(RESURRECTION_TOKEN_ID), 1)
    run.leader.take_damage(1000)
    meta = MetaState()
    result = run.on_death(meta, data)
    assert result.revived is False
    assert not run.alive
    summary = run.summary(cause="slain", revived=False)
    assert summary.floor_reached == 1 and summary.cause == "slain"
