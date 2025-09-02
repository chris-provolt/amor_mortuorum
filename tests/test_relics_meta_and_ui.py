from __future__ import annotations

import json
from pathlib import Path

from amor.core.events import EventBus
from amor.meta.meta_store import MetaStore
from amor.meta.relics_data import RelicsData
from amor.meta.relics_manager import RelicsManager
from amor.ui.graveyard.relics_panel import GraveyardRelicsPanel


def load_relics_data() -> RelicsData:
    data_path = Path(__file__).parent.parent / "data" / "relics.json"
    return RelicsData.from_file(data_path)


def test_graveyard_panel_updates_and_persists(tmp_path: Path):
    # Arrange
    meta_path = tmp_path / "meta.json"
    store = MetaStore(meta_path)
    bus = EventBus()
    relics_data = load_relics_data()
    mgr = RelicsManager(store, relics_data, bus)
    panel = GraveyardRelicsPanel(mgr, bus)

    # Initial state
    assert mgr.collected_count() == 0
    assert mgr.final_collected() is False
    assert panel.text == "Relics: 0/9 | Final: \u2717"  # ✗

    # Act: collect first fragment
    first_fragment = relics_data.fragment_ids[0]
    changed = mgr.collect_relic(first_fragment)

    # Assert: state changed, UI updated, persisted
    assert changed is True
    assert mgr.collected_count() == 1
    assert panel.text == "Relics: 1/9 | Final: \u2717"

    saved = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved["relics"]["collected_ids"] == [first_fragment]
    assert saved["relics"]["final_collected"] is False

    # Collect duplicate should not change state
    changed_dup = mgr.collect_relic(first_fragment)
    assert changed_dup is False
    assert mgr.collected_count() == 1
    assert panel.text == "Relics: 1/9 | Final: \u2717"

    # Collect remaining fragments
    for fid in relics_data.fragment_ids[1:]:
        mgr.collect_relic(fid)
    assert mgr.collected_count() == 9
    assert panel.text == "Relics: 9/9 | Final: \u2717"

    # Collect final relic
    changed_final = mgr.collect_final_relic()
    assert changed_final is True
    assert mgr.final_collected() is True
    assert panel.text == "Relics: 9/9 | Final: \u2713"  # ✓

    saved2 = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved2["relics"]["collected_ids"] == relics_data.fragment_ids
    assert saved2["relics"]["final_collected"] is True


def test_invalid_and_type_checks(tmp_path: Path):
    meta_path = tmp_path / "meta.json"
    store = MetaStore(meta_path)
    bus = EventBus()
    relics_data = load_relics_data()
    mgr = RelicsManager(store, relics_data, bus)

    # Unknown id should raise
    try:
        mgr.collect_relic("unknown_id")
        assert False, "Expected KeyError"
    except KeyError:
        pass

    # Collecting final via fragment method should raise
    try:
        mgr.collect_relic(relics_data.final.id)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    # Collecting final twice returns False second time
    assert mgr.collect_final_relic() is True
    assert mgr.collect_final_relic() is False
