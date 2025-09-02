import pytest

from amor.events import get_event_bus, EventType
from amor.relics import RelicPassiveManager
from amor.relics.relics import RELICS
from amor.stats import GlobalModifiers, StatsCalculator


def test_toggle_applies_global_effect_and_publishes_event():
    bus = get_event_bus()
    mgr = RelicPassiveManager()

    received = []

    def on_change(evt):
        received.append(evt.payload["modifiers"])  # payload is dict form of GlobalModifiers

    bus.subscribe(EventType.RELIC_PASSIVES_CHANGED, on_change)

    # Acquire and enable a known relic
    rid = "ferryman_coin"
    assert rid in RELICS

    mgr.acquire_relic(rid)
    mgr.enable(rid)

    # Should have published at least one aggregate change
    assert len(received) >= 1

    # Verify the global modifiers now include gold multiplier 1.05
    mods = mgr.get_global_modifiers()
    assert isinstance(mods, GlobalModifiers)
    assert pytest.approx(mods.gold_find_multiplier, rel=1e-6) == 1.05

    # Clean up subscription
    bus.unsubscribe(EventType.RELIC_PASSIVES_CHANGED, on_change)


def test_combination_and_stats_application():
    mgr = RelicPassiveManager()

    # Acquire two relics and enable them
    mgr.set_owned_many({"veil_fragment", "grave_tuned_charm"})
    mgr.enable("veil_fragment")  # +2% HP, +2% DEF
    mgr.enable("grave_tuned_charm")  # +2% ATK

    mods = mgr.get_global_modifiers()

    # Multiplicative stacking across stats
    assert pytest.approx(mods.stat_multipliers["HP"], rel=1e-6) == 1.02
    assert pytest.approx(mods.stat_multipliers["DEF"], rel=1e-6) == 1.02
    assert pytest.approx(mods.stat_multipliers["ATK"], rel=1e-6) == 1.02
    assert pytest.approx(mods.stat_multipliers["SPD"], rel=1e-6) == 1.0

    # Apply to a base stats dictionary
    base = {"HP": 100, "ATK": 50, "DEF": 25, "SPD": 10}
    result = StatsCalculator.apply_modifiers(base, mods)
    assert pytest.approx(result["HP"], rel=1e-6) == 102.0
    assert pytest.approx(result["ATK"], rel=1e-6) == 51.0
    assert pytest.approx(result["DEF"], rel=1e-6) == 25.5
    assert pytest.approx(result["SPD"], rel=1e-6) == 10.0


def test_enable_requires_ownership():
    mgr = RelicPassiveManager()
    rid = "lantern_wisp"  # not owned initially
    with pytest.raises(PermissionError):
        mgr.enable(rid)

    # After acquiring, enabling should succeed
    mgr.acquire_relic(rid)
    mgr.enable(rid)
    assert mgr.is_enabled(rid) is True


def test_persistence_round_trip():
    mgr = RelicPassiveManager()
    mgr.set_owned_many({"ferryman_coin", "lantern_wisp"})
    mgr.enable("ferryman_coin")

    state = mgr.to_dict()

    # Create a fresh manager and load the state
    mgr2 = RelicPassiveManager()
    mgr2.load_dict(state)

    assert mgr2.is_owned("ferryman_coin") is True
    assert mgr2.is_enabled("ferryman_coin") is True
    assert mgr2.is_owned("lantern_wisp") is True
    assert mgr2.is_enabled("lantern_wisp") is False

    # Verify aggregate matches expectation
    mods = mgr2.get_global_modifiers()
    assert pytest.approx(mods.gold_find_multiplier, rel=1e-6) == 1.05
    assert mods.light_radius_delta == 0
