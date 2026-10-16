import pytest

from amormortuorum.data import DataError, GameData
from amormortuorum.persistence import MetaState, SaveManager
from amormortuorum.scenes.profiles import next_profile_name
from amormortuorum.systems.stats import (
    bump,
    check_achievements,
    derived_stats,
    record_max,
    stat_rows,
)


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_bump_record_and_derived(data):
    meta = MetaState()
    assert bump(meta, "steps") == 1
    assert bump(meta, "steps", 9) == 10
    assert record_max(meta, "deepest_floor", 7) == 7
    assert record_max(meta, "deepest_floor", 3) == 7
    meta.relics.add("veil_1")
    meta.deepest_floor = 12
    d = derived_stats(meta)
    assert d["relics"] == 1 and d["deepest_floor"] == 12 and d["steps"] == 10
    labels = dict(stat_rows(meta))
    assert labels["Steps taken"] == 10 and labels["Relics found"] == 1


def test_achievements_unlock_once_and_persist(data):
    meta = MetaState()
    assert check_achievements(meta, data) == []
    bump(meta, "battles_won")
    new = check_achievements(meta, data)
    assert [a.id for a in new] == ["first_blood"]
    assert check_achievements(meta, data) == []  # not twice
    bump(meta, "enemies_slain", 1000)
    ids = {a.id for a in check_achievements(meta, data)}
    assert ids == {"gravedigger", "ossuary"}
    clone = MetaState.from_dict(meta.to_dict())
    assert clone.achievements == meta.achievements and clone.stats == meta.stats


def test_achievement_data_validation(data):
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "src" / "amormortuorum" / "data"

    def read(name):
        return json.loads((folder / name).read_text(encoding="utf-8"))

    raw = dict(
        items=read("items.json"), enemies=read("enemies.json"),
        loot_tables=read("loot_tables.json"), floor_tiers=read("floor_tiers.json"),
        relics=read("relics.json"), encounters=read("encounters.json"), shop=read("shop.json"),
        xp_curve=read("xp_curve.json"), bosses=read("bosses.json"), skills=read("skills.json"),
        companions=read("companions.json"), balance=read("balance.json"),
    )
    raw["achievements"] = [{"id": "x", "name": "x", "stat": "nope", "at_least": 1}]
    with pytest.raises(DataError, match="unknown stat"):
        GameData.from_raw(**raw)


def test_profile_listing_and_naming(tmp_path):
    assert SaveManager.list_profiles(tmp_path) == []
    SaveManager(root_dir=tmp_path, profile_id="default")
    SaveManager(root_dir=tmp_path, profile_id="profile2")
    assert SaveManager.list_profiles(tmp_path) == ["default", "profile2"]
    assert next_profile_name(["default", "profile2"]) == "profile3"
    assert next_profile_name([]) == "profile2"


def test_every_tracked_stat_has_a_label_and_new_counters_unlock(data):
    from amormortuorum.data import TRACKED_STATS
    from amormortuorum.systems.stats import STAT_LABELS

    assert set(TRACKED_STATS) == set(STAT_LABELS)
    meta = MetaState()
    bump(meta, "bounties", 10)
    bump(meta, "ambushes", 9)
    ids = {a.id for a in check_achievements(meta, data)}
    assert "bounty_hunter" in ids and "silent_knife" not in ids
