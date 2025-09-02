import json

from amormortuorum.domain.run_summary import RunOutcome, RunSummary, LootItem, Relic


def test_run_summary_formatting_contains_core_metrics():
    summary = RunSummary.from_run_stats(
        outcome=RunOutcome.DEATH,
        depth_reached=13,
        enemies_defeated=37,
        loot=[LootItem("Iron Sword", rarity="Common"), LootItem("Potion", qty=3)],
        relics=[Relic(id="veil_eye", name="Eye of the Veil")],
        gold_collected=124,
        duration_seconds=372,
        seed=987654,
    )

    lines = summary.format_lines(width=60)

    # Titles
    assert any("You Died" in l for l in lines)
    assert any("Fell on Floor 13" in l for l in lines)

    # Metrics
    assert any("Floors cleared: 12" in l for l in lines)
    assert any("Enemies defeated: 37" in l for l in lines)
    assert any("Gold collected: 124" in l for l in lines)
    assert any("Time: 6m 12s" in l for l in lines)
    assert any("Run Seed: 987654" in l for l in lines)

    # Loot and relics
    loot_section_idx = lines.index(next(l for l in lines if l.startswith("Loot acquired")))
    relic_section_idx = lines.index(next(l for l in lines if l.startswith("Relics found")))
    assert loot_section_idx < relic_section_idx

    assert any("Iron Sword" in l for l in lines)
    assert any("Potion x3" in l for l in lines)
    assert any("Eye of the Veil" in l for l in lines)

    # Footer
    assert any("Press Enter/Space" in l for l in lines)


def test_run_summary_serialization_roundtrip_keys_present():
    s = RunSummary.from_run_stats(
        outcome=RunOutcome.EXIT,
        depth_reached=5,
        enemies_defeated=8,
        loot=[],
        relics=[],
        gold_collected=0,
    )
    d = s.to_dict()

    # Must contain essential keys and values
    assert d["outcome"] == "exit"
    assert d["depth_reached"] == 5
    assert d["floors_cleared"] == 4
    assert d["enemies_defeated"] == 8
    assert isinstance(d["loot"], list) and d["loot"] == []
    assert isinstance(d["relics"], list) and d["relics"] == []

    # JSON serializable
    json.dumps(d)
