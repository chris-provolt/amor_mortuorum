from collections import Counter
from random import Random

import pytest

from amormortuorum.data import QUALITIES, GameData
from amormortuorum.systems.loot import (
    roll_chest,
    roll_chest_gold,
    roll_gold,
    roll_quality,
    tier_for_floor,
)


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_tier_for_floor(data):
    assert tier_for_floor(1, data) == "T1"
    assert tier_for_floor(20, data) == "T1"
    assert tier_for_floor(21, data) == "T2"
    assert tier_for_floor(99, data) == "T5"


def test_roll_quality_distribution_follows_weights(data):
    rng = Random(42)
    weights = data.loot_tables["T1"]
    counts = Counter(roll_quality(rng, weights) for _ in range(10_000))
    assert counts["Common"] > counts["Uncommon"] > counts["Rare"] > counts["Epic"]
    assert 0.55 < counts["Common"] / 10_000 < 0.65


def test_roll_quality_deeper_floors_are_richer(data):
    rng_a, rng_b = Random(1), Random(1)
    shallow = Counter(roll_quality(rng_a, data.loot_tables["T1"]) for _ in range(5000))
    deep = Counter(roll_quality(rng_b, data.loot_tables["T5"]) for _ in range(5000))
    assert deep["Epic"] > shallow["Epic"]
    assert deep["Common"] < shallow["Common"]


def test_roll_quality_rejects_empty_weights():
    with pytest.raises(ValueError):
        roll_quality(Random(1), {"Common": 0})


def test_roll_chest_is_deterministic_and_returns_known_items(data):
    a = [roll_chest(Random(7), floor, data).id for floor in (1, 30, 99)]
    b = [roll_chest(Random(7), floor, data).id for floor in (1, 30, 99)]
    assert a == b
    for item_id in a:
        assert data.has_item(item_id)


def test_roll_chest_falls_back_when_quality_bucket_is_empty(data):
    # Strip every Epic item; an Epic roll must fall back to a lower quality.
    stripped = GameData(
        items={k: v for k, v in data.items.items() if v.quality != "Epic"},
        enemies=data.enemies,
        loot_tables={"T1": {"Epic": 1}},
        tiers=data.tiers,
        relics=data.relics,
        encounters=data.encounters,
        shop_pool=data.shop_pool,
    )
    item = roll_chest(Random(3), 1, stripped)
    assert item.quality in QUALITIES and item.quality != "Epic"


def test_gold_scales_with_depth():
    low = roll_gold(Random(1), 1)
    high = roll_gold(Random(1), 90)
    assert 7 <= low <= 14
    assert high > low


def test_chest_gold_chance(data):
    rolls = [roll_chest_gold(Random(i), 5) for i in range(400)]
    hits = [g for g in rolls if g is not None]
    assert 0.15 < len(hits) / 400 < 0.35
    assert all(g > 0 for g in hits)
