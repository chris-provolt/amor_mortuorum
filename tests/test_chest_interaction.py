import pytest

from amor.core.random import RandomSource
from amor.items.models import ItemQuality
from amor.player.inventory import Inventory
from amor.player.player import Player
from amor.world.entities.chest import Chest, ChestAlreadyOpenedError
from amor.loot.quality import get_floor_tier, get_quality_weights_for_floor, DEFAULT_QUALITY_WEIGHTS


def test_floor_to_tier_mapping():
    assert get_floor_tier(1) == 1
    assert get_floor_tier(19) == 1
    assert get_floor_tier(20) == 2
    assert get_floor_tier(39) == 2
    assert get_floor_tier(40) == 3
    assert get_floor_tier(59) == 3
    assert get_floor_tier(60) == 4
    assert get_floor_tier(79) == 4
    assert get_floor_tier(80) == 5
    assert get_floor_tier(99) == 5
    # Clamp
    assert get_floor_tier(0) == 1
    assert get_floor_tier(150) == 5


def test_chest_adds_item_and_consumes():
    player = Player(inventory=Inventory())
    chest = Chest(id="test_chest_1")
    rng = RandomSource(seed=12345)

    item = chest.interact(player, floor=1, rng=rng)

    # Item appears in inventory
    assert len(player.inventory) == 1
    assert player.inventory.items[0].id == item.id

    # Chest is consumed
    assert chest.consumed is True

    # Second interaction should fail
    with pytest.raises(ChestAlreadyOpenedError):
        chest.interact(player, floor=1, rng=rng)


def test_tier_based_quality_weights_override_forces_quality():
    player = Player(inventory=Inventory())
    chest = Chest(id="test_chest_2")
    rng = RandomSource(seed=42)

    # Force legendary quality via override weights
    weights_override = {
        ItemQuality.COMMON: 0,
        ItemQuality.UNCOMMON: 0,
        ItemQuality.RARE: 0,
        ItemQuality.EPIC: 0,
        ItemQuality.LEGENDARY: 1,
    }

    item = chest.interact(player, floor=1, rng=rng, quality_weights_override=weights_override)

    assert item.quality == ItemQuality.LEGENDARY
    assert len(player.inventory) == 1


def test_default_weights_applied_for_tier():
    # Validate that the weights returned are the defaults when no config present
    # Here we just check equality for a representative floor in each tier
    for floor, expected_tier in [(1, 1), (25, 2), (41, 3), (70, 4), (95, 5)]:
        weights = get_quality_weights_for_floor(floor)
        assert weights == DEFAULT_QUALITY_WEIGHTS[expected_tier]
