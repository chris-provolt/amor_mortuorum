from amormortuorum.core.rng import RNG
from amormortuorum.items.loot import LootItem, LootTable


def test_depth_filtering_excludes_shallow_items():
    rng = RNG(seed=123)
    table = LootTable()
    table.extend([
        LootItem(name="Shallow Trinket", min_depth=1, max_depth=10, weight=10, quality=1),
        LootItem(name="Mid Charm", min_depth=11, max_depth=49, weight=10, quality=2),
        LootItem(name="Deep Relic", min_depth=50, max_depth=99, weight=10, quality=3),
    ])

    # At depth 60, only Deep Relic should be eligible
    for _ in range(200):
        item = table.roll(depth=60, rng=rng)
        assert item.name == "Deep Relic"


def test_weighted_distribution_bias():
    rng = RNG(seed=42)
    table = LootTable()
    table.extend([
        LootItem(name="Rare Sword", min_depth=1, max_depth=99, weight=1, quality=3),
        LootItem(name="Common Sword", min_depth=1, max_depth=99, weight=9, quality=1),
    ])

    trials = 10_000
    rare_count = 0
    for _ in range(trials):
        it = table.roll(depth=5, rng=rng)
        if it.name == "Rare Sword":
            rare_count += 1

    p_rare = rare_count / trials
    # Expect around 10% (1 / (1 + 9)), allow generous tolerance for randomness
    assert 0.07 <= p_rare <= 0.13, f"p_rare={p_rare} out of expected range"


def test_theme_filtering():
    rng = RNG(seed=7)
    table = LootTable()
    table.extend([
        LootItem(name="Fire Scroll I", min_depth=1, max_depth=99, weight=5, quality=1, theme="fire"),
        LootItem(name="Fire Scroll II", min_depth=1, max_depth=99, weight=5, quality=2, theme="fire"),
        LootItem(name="Ice Scroll I", min_depth=1, max_depth=99, weight=5, quality=1, theme="ice"),
    ])

    for _ in range(100):
        item = table.roll(depth=15, rng=rng, theme="fire")
        assert item.theme == "fire"


def test_roll_raises_when_no_eligible_items():
    rng = RNG(seed=1)
    table = LootTable()
    table.add_item(LootItem(name="A", min_depth=1, max_depth=10, weight=1))
    try:
        table.roll(depth=50, rng=rng)
    except ValueError as e:
        assert "No eligible" in str(e)
    else:
        assert False, "Expected ValueError when no eligible items"
