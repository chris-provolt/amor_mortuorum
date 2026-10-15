import pytest

from amormortuorum.data import DataError, GameData, XpCurve
from amormortuorum.systems.entities import new_player
from amormortuorum.systems.progression import grant_xp, sync_level, xp_to_next_level


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_curve_lookups(data):
    curve = data.xp_curve
    assert curve.xp_for_level(1) == 0
    assert curve.xp_for_level(2) == 25
    assert curve.level_for_xp(0) == 1
    assert curve.level_for_xp(24) == 1
    assert curve.level_for_xp(25) == 2
    assert curve.level_for_xp(10**9) == curve.max_level


def test_grant_xp_levels_up_and_raises_stats(data):
    p = new_player()
    base = p.stats.to_dict()
    assert xp_to_next_level(p, data) == 25

    ups = grant_xp(p, 24, data)
    assert ups == [] and p.level == 1

    ups = grant_xp(p, 1, data)
    assert [u.level for u in ups] == [2]
    assert p.stats.max_hp == base["max_hp"] + 6
    assert p.stats.hp == base["hp"] + 6  # healed by the gain
    assert p.stats.atk == base["atk"] + 1 and p.stats.df == base["df"] + 1  # df every 2
    assert p.stats.spd == base["spd"]  # level 2 is not a speed level
    assert "Level 2!" in ups[0].describe()

    # Several levels at once; level 3 grants SPD (every spd == 3) but no DEF
    ups = grant_xp(p, 100, data)
    assert [u.level for u in ups] == [3]
    assert p.stats.spd == base["spd"] + 1
    assert p.stats.df == base["df"] + 1
    assert sync_level(p, data) == []  # idempotent


def test_level_cap(data):
    p = new_player()
    grant_xp(p, 10**9, data)
    assert p.level == data.xp_curve.max_level
    assert xp_to_next_level(p, data) is None
    with pytest.raises(ValueError):
        grant_xp(p, -1, data)


def test_bad_curves_rejected(data):
    bad = GameData(
        items=data.items, enemies=data.enemies, loot_tables=data.loot_tables,
        tiers=data.tiers, relics=data.relics, encounters=data.encounters,
        shop_pool=data.shop_pool, xp_curve=XpCurve(max_level=3, thresholds=(0, 10, 5)),
    )
    with pytest.raises(DataError, match="increasing"):
        bad.validate()
    bad.xp_curve = XpCurve(max_level=2, thresholds=(5, 10))
    with pytest.raises(DataError, match="level 1"):
        bad.validate()
