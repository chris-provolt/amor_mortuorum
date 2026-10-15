import json
from pathlib import Path

import pytest

from amormortuorum.data import MAX_FLOOR, QUALITIES, DataError, GameData

DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "amormortuorum" / "data"


def _raw():
    def read(name):
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))

    return dict(
        items=read("items.json"),
        enemies=read("enemies.json"),
        loot_tables=read("loot_tables.json"),
        floor_tiers=read("floor_tiers.json"),
        relics=read("relics.json"),
        encounters=read("encounters.json"),
        shop=read("shop.json"),
    )


def test_shipped_data_loads_and_is_consistent():
    data = GameData.load()
    assert data.item("res_token").revive is True
    assert data.item("blade_bone").slot == "weapon"
    assert data.item("potion_small").usable_in_combat
    assert not data.item("blade_bone").usable_in_combat
    assert [t.name for t in data.tiers] == ["T1", "T2", "T3", "T4", "T5"]
    assert data.tier_for_floor(1).name == "T1"
    assert data.tier_for_floor(MAX_FLOOR).name == "T5"
    assert len(data.relics) == 10 and data.relic_ids[-1] == "veil_final"
    for q in QUALITIES:
        assert data.items_of_quality(q), f"no items of quality {q}"
    for tier in data.tiers:
        assert tier.name in data.loot_tables
        assert tier.name in data.encounters
    for item_id in data.shop_pool:
        assert data.has_item(item_id)


def test_load_from_explicit_directory_matches_package():
    assert GameData.load(DATA_DIR).items.keys() == GameData.load().items.keys()


def test_unknown_lookups_raise():
    data = GameData.load()
    with pytest.raises(DataError):
        data.item("nope")
    with pytest.raises(DataError):
        data.enemy("nope")
    with pytest.raises(DataError):
        data.tier_for_floor(0)


def test_duplicate_item_id_rejected():
    raw = _raw()
    raw["items"].append(dict(raw["items"][0]))
    with pytest.raises(DataError, match="duplicate"):
        GameData.from_raw(**raw)


def test_missing_resurrection_token_rejected():
    raw = _raw()
    raw["items"] = [it for it in raw["items"] if it["id"] != "res_token"]
    with pytest.raises(DataError, match="res_token"):
        GameData.from_raw(**raw)


def test_tier_gap_rejected():
    raw = _raw()
    raw["floor_tiers"][1]["start"] = 25
    with pytest.raises(DataError, match="gap"):
        GameData.from_raw(**raw)


def test_formation_with_unknown_enemy_rejected():
    raw = _raw()
    raw["encounters"]["T1"]["formations"][0]["enemies"] = ["dragon"]
    with pytest.raises(DataError, match="unknown enemy"):
        GameData.from_raw(**raw)


def test_shop_unknown_item_rejected():
    raw = _raw()
    raw["shop"]["mystery"] = {"price": 1, "qty_range": [1, 1]}
    with pytest.raises(DataError, match="shop"):
        GameData.from_raw(**raw)


def test_bad_quality_rejected():
    raw = _raw()
    raw["items"][0]["quality"] = "Legendary"
    with pytest.raises(DataError, match="quality"):
        GameData.from_raw(**raw)


def test_missing_file_reports_name(tmp_path):
    with pytest.raises(DataError, match="items.json"):
        GameData.load(tmp_path)
