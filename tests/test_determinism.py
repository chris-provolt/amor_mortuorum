from __future__ import annotations

import json

from amor.rng import RNGManager
from amor.dungeon.generation import DungeonGenerator
from amor.loot.chest import ChestGenerator
from amor.config import Settings
from amor.game import generate_floor


def test_same_seed_same_floor_layout_and_chests_equal():
    seed = "test-seed-123"
    floor = 7

    rngm1 = RNGManager(seed)
    rngm2 = RNGManager(seed)

    d1 = DungeonGenerator(rngm1, width=48, height=48)
    d2 = DungeonGenerator(rngm2, width=48, height=48)

    layout1 = d1.generate(floor)
    layout2 = d2.generate(floor)

    assert layout1.grid == layout2.grid, "Grids should be identical with same seed+floor"
    assert layout1.chests == layout2.chests, "Chest positions should be identical with same seed+floor"
    assert layout1.signature() == layout2.signature(), "Layout signatures should match"

    cgen1 = ChestGenerator(rngm1)
    cgen2 = ChestGenerator(rngm2)

    ch1 = cgen1.generate_for_positions(floor, layout1.chests)
    ch2 = cgen2.generate_for_positions(floor, layout2.chests)

    assert [c.item_id for c in ch1] == [c.item_id for c in ch2], "Chest loot should match with same seed+floor"


def test_different_seed_changes_layout_or_loot():
    seed_a = "seed-A"
    seed_b = "seed-B"
    floor = 10

    rngm_a = RNGManager(seed_a)
    rngm_b = RNGManager(seed_b)

    d_a = DungeonGenerator(rngm_a, width=48, height=48)
    d_b = DungeonGenerator(rngm_b, width=48, height=48)

    layout_a = d_a.generate(floor)
    layout_b = d_b.generate(floor)

    # It's possible (but extremely unlikely) for the entire grid to match accidentally.
    # We assert that either the signature or chest positions differ.
    different = layout_a.signature() != layout_b.signature() or layout_a.chests != layout_b.chests
    assert different, "Different seeds should result in different layouts and/or chest positions"


def test_same_seed_different_floors_differ():
    seed = "same-seed"

    rngm = RNGManager(seed)

    d = DungeonGenerator(rngm, width=48, height=48)

    layout5 = d.generate(5)
    layout6 = d.generate(6)

    assert layout5.signature() != layout6.signature(), "Different floors should produce different layouts"


def test_high_level_generate_floor_is_deterministic():
    settings = Settings(seed="cli-seed", width=40, height=40)

    a = generate_floor(settings, 12)
    b = generate_floor(settings, 12)

    assert a["layout"]["signature"] == b["layout"]["signature"]
    assert a["chests"] == b["chests"], "Chest contents should match"

    # Ensure output is JSON-serializable
    json.dumps(a)
    json.dumps(b)
