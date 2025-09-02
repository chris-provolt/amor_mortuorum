from __future__ import annotations

import random
from pathlib import Path

import pytest

from src.amor.encounters.enemy_registry import EnemyRegistry
from src.amor.encounters.formations import (
    load_formations_from_path,
    load_formations_from_dict,
    FormationSelector,
    floor_to_tier,
)


DATA_PATH = Path("data/encounters/formations.json")


def test_load_formations_and_select_for_floor():
    fs = load_formations_from_path(DATA_PATH)
    selector = FormationSelector(fs)

    rng = random.Random(1337)
    # Select several floors and ensure we get non-empty spawn lists
    for floor in [1, 5, 12, 23, 35, 47, 58, 69, 83, 95]:
        spawns = selector.select_for_floor(floor, rng)
        assert isinstance(spawns, list) and spawns, f"No spawns for floor {floor}"
        # Validate that all enemies exist and counts are positive
        for enemy, count in spawns:
            assert fs.registry.has(enemy.id)
            assert count > 0
            # Ensure tier appropriateness: enemy tier should not exceed floor tier by more than 1 (soft rule)
            tier = floor_to_tier(floor)
            assert enemy.tier <= tier + 1


def test_expected_difficulty_monotonic_increase():
    fs = load_formations_from_path(DATA_PATH)
    # Compute expected (weighted) difficulty by tier and ensure monotonic increase
    diffs = [fs.expected_difficulty_for_tier(t) for t in range(1, 11)]
    for earlier, later in zip(diffs, diffs[1:]):
        assert later > earlier, f"Expected difficulty to increase, got {earlier} -> {later}"


def test_weighted_selection_bias_with_minimal_dataset():
    # Minimal dataset: two formations A and B with 9:1 weights in tier 1
    data = {
        "formations": [
            {
                "id": "A",
                "members": [{"enemy": "slime", "count": 1}],
                "weights": {"1": 9}
            },
            {
                "id": "B",
                "members": [{"enemy": "slime", "count": 2}],
                "weights": {"1": 1}
            },
        ]
    }
    fs = load_formations_from_dict(data, registry=EnemyRegistry())

    rng = random.Random(12345)
    counts = {"A": 0, "B": 0}
    for _ in range(1000):
        f = fs.select_for_tier(1, rng)
        counts[f.id] += 1

    # With 9:1 weights, A should be the majority ~90%
    assert counts["A"] > 800
    assert counts["B"] < 200


def test_invalid_enemy_reference_raises():
    data = {
        "formations": [
            {
                "id": "bad",
                "members": [{"enemy": "nonexistent_enemy", "count": 1}],
                "weights": {"1": 1}
            }
        ]
    }
    with pytest.raises(ValueError):
        load_formations_from_dict(data)


def test_spawn_counts_and_resolve():
    fs = load_formations_from_path(DATA_PATH)
    # Pick a tier with multiple formations
    f = fs.select_for_tier(5, random.Random(7))
    spawns = fs.spawn(f)
    # Validate that total count equals sum of formation members
    total_count = sum(c for _, c in spawns)
    assert total_count == sum(m.count for m in f.members)


def test_floor_to_tier_mapping():
    # Boundary checks
    assert floor_to_tier(1) == 1
    assert floor_to_tier(10) == 1
    assert floor_to_tier(11) == 2
    assert floor_to_tier(20) == 2
    assert floor_to_tier(90) == 9
    assert floor_to_tier(99) == 10
    # Clamping
    assert floor_to_tier(0) == 1
    assert floor_to_tier(150) == 10
