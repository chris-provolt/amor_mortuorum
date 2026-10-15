from random import Random

import pytest

from amormortuorum.data import DataError, GameData
from amormortuorum.persistence import MetaState
from amormortuorum.systems.combat import Battle
from amormortuorum.systems.entities import Enemy
from amormortuorum.systems.loot import chest_relic_pool, relic_chest_chance, roll_relic
from amormortuorum.systems.relics import (
    apply_passives,
    collection_rows,
    describe_passive,
    passive_totals,
)
from amormortuorum.systems.run import new_run


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_every_relic_has_a_known_passive(data):
    for relic in data.relics:
        assert relic.passive, relic.id
    assert data.relic("veil_final").is_final
    with pytest.raises(DataError):
        data.relic("veil_99")


def test_passive_totals_and_application(data):
    meta = MetaState()
    assert passive_totals(meta, data) == {}
    meta.relics.add("veil_2")  # ATK +1
    meta.relics.add("veil_9")  # ATK +1, DEF +1
    totals = passive_totals(meta, data)
    assert totals == {"atk": 2, "df": 1}
    assert describe_passive(totals) == "ATK +2, DEF +1"

    run = new_run(data, seed=1, meta=meta)
    p = run.leader
    assert p.bonuses == totals
    assert p.effective_atk(data) == p.stats.atk + 2
    assert p.effective_df(data) == p.stats.df + 1

    meta.relics.add("veil_1")  # sight +2
    assert apply_passives(run, meta, data)["fov"] == 2
    assert p.bonus("fov") == 2
    # Bonuses are derived, never serialized
    assert "bonuses" not in p.to_dict()


def test_reward_percent_passives(data):
    meta = MetaState()
    meta.relics.add("veil_3")  # gold +15%
    meta.relics.add("veil_final")  # xp +25%, gold +25%
    run = new_run(data, seed=1, meta=meta)
    enemy = Enemy.from_def(data.enemy("bone_guard"))  # 10 xp, 7 gold
    battle = Battle(run.party, [enemy], Random(1), data)
    gold_before = run.leader.gold
    xp, gold = battle.apply_rewards()
    assert xp == 10 * 125 // 100
    assert gold == 7 * 140 // 100
    assert run.leader.gold == gold_before + gold


def test_chest_relic_pool_excludes_boss_relics_and_collected(data):
    pool_ids = {r.id for r in chest_relic_pool(data, [])}
    boss_relics = {b.relic_id for b in data.bosses.values()}
    assert pool_ids == {"veil_1", "veil_2", "veil_4", "veil_5", "veil_7"}
    assert not pool_ids & boss_relics
    remaining = {r.id for r in chest_relic_pool(data, ["veil_1", "veil_2"])}
    assert remaining == {"veil_4", "veil_5", "veil_7"}
    assert chest_relic_pool(data, pool_ids) == []


def test_roll_relic_rate_and_determinism(data):
    assert relic_chest_chance(1, data) == pytest.approx(0.02)
    assert relic_chest_chance(99, data) == pytest.approx(0.08)
    hits = sum(1 for i in range(3000) if roll_relic(Random(i), 90, data, []) is not None)
    assert 0.05 < hits / 3000 < 0.11
    a = [roll_relic(Random(7), f, data, []) for f in range(1, 60)]
    b = [roll_relic(Random(7), f, data, []) for f in range(1, 60)]
    assert a == b
    everything = {"veil_1", "veil_2", "veil_4", "veil_5", "veil_7"}
    assert roll_relic(Random(1), 50, data, everything) is None


def test_collection_rows_order_and_flags(data):
    meta = MetaState()
    meta.relics.add("veil_5")
    rows = collection_rows(meta, data)
    assert [r.id for r, _ in rows] == data.relic_ids
    assert dict((r.id, got) for r, got in rows)["veil_5"] is True
    assert sum(got for _, got in rows) == 1
