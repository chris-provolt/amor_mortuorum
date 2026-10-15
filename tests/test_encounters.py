from collections import Counter
from random import Random

import pytest

from amormortuorum.data import GameData
from amormortuorum.systems.encounters import (
    ENCOUNTER_CAP,
    combat_rng,
    encounter_chance,
    encounter_rng,
    roll_formation,
    step_encounter,
)
from amormortuorum.systems.entities import Enemy


@pytest.fixture(scope="module")
def data() -> GameData:
    return GameData.load()


def test_encounter_chance_grows_then_caps():
    assert encounter_chance(0.05, 0) == pytest.approx(0.05)
    assert encounter_chance(0.05, 10) == pytest.approx(0.075)
    assert encounter_chance(0.05, 10, cap=0.5, growth=0.1) == pytest.approx(0.10)
    assert encounter_chance(0.05, 1000) == ENCOUNTER_CAP
    assert encounter_chance(0.9, 0) == ENCOUNTER_CAP
    assert encounter_chance(0.05, -5) == pytest.approx(0.05)


def test_step_encounter_is_deterministic(data):
    def rolls(seed: int):
        rng = encounter_rng(seed, 1)
        return [step_encounter(rng, 1, i, data) for i in range(200)]

    assert rolls(3) == rolls(3)
    assert rolls(3) != rolls(4)
    assert any(rolls(3)) and not all(rolls(3))


def test_step_encounter_rate_tracks_tier_chance(data):
    rng = Random(0)
    hits = sum(step_encounter(rng, 1, 0, data) for _ in range(20000))
    assert hits / 20000 == pytest.approx(data.encounters["T1"].step_chance, abs=0.01)


def test_roll_formation_returns_known_fresh_enemies(data):
    rng = Random(1)
    for floor in (1, 25, 45, 70, 99):
        enemies = roll_formation(rng, floor, data)
        assert enemies
        tier = data.tier_for_floor(floor).name
        allowed = {eid for f in data.encounters[tier].formations for eid in f.enemies}
        for e in enemies:
            assert isinstance(e, Enemy)
            assert e.def_id in allowed
            expected = Enemy.from_def(data.enemy(e.def_id), floor, data.balance)
            assert e.is_alive and e.stats.hp == expected.stats.hp
            assert e.stats.hp >= data.enemy(e.def_id).hp  # scaled up with depth
    # Fresh instances each roll
    a = roll_formation(Random(5), 1, data)
    b = roll_formation(Random(5), 1, data)
    assert [e.def_id for e in a] == [e.def_id for e in b]
    assert all(x is not y for x, y in zip(a, b))


def test_roll_formation_respects_weights(data):
    rng = Random(123)
    counts = Counter(
        tuple(e.def_id for e in roll_formation(rng, 1, data)) for _ in range(2000)
    )
    heaviest = max(data.encounters["T1"].formations, key=lambda f: f.weight)
    assert counts.most_common(1)[0][0] == tuple(heaviest.enemies)


def test_rng_streams_are_distinct_and_reproducible():
    assert encounter_rng(1, 1).random() == encounter_rng(1, 1).random()
    assert encounter_rng(1, 1).random() != encounter_rng(1, 2).random()
    assert combat_rng(1, 1, 0).random() == combat_rng(1, 1, 0).random()
    assert combat_rng(1, 1, 0).random() != combat_rng(1, 1, 1).random()
    assert combat_rng(1, 1, 0).random() != encounter_rng(1, 1).random()
