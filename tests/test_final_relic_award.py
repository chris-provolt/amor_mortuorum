import json
import os
from pathlib import Path

from amor.core.save_service import SaveService
from amor.game.boss import BossDefeatService
from amor.game.events import BossDefeatedEvent
from amor.meta.relics import RelicDefinitions, RelicManager
from amor.ui.relic_collection_view import RelicCollectionView


def test_award_final_relic_only_once_and_persisted(tmp_path: Path):
    save_dir = tmp_path / "saves"
    save = SaveService(str(save_dir), namespace="testplayer")
    defs = RelicDefinitions()  # Will use data/relics.json if present, else defaults
    relics = RelicManager(save, defs)

    final_id = defs.final_relic_id()

    # Initially not collected
    assert not relics.is_collected(final_id)

    svc = BossDefeatService(relics)

    event = BossDefeatedEvent(floor=99, boss_id="final_boss", is_final=True, run_id="run-1")

    # First defeat awards the relic
    awarded = svc.on_boss_defeated(event)
    assert awarded is True
    assert relics.is_collected(final_id)

    # Verify persisted to disk
    save_path = os.path.join(str(save_dir), "testplayer.save.json")
    assert os.path.exists(save_path)
    with open(save_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert final_id in data["relics"]["collected"]

    # Reload managers to ensure persistence across process lifecycle
    save2 = SaveService(str(save_dir), namespace="testplayer")
    relics2 = RelicManager(save2, defs)
    assert relics2.is_collected(final_id)
    prev_count = relics2.collected_count()

    svc2 = BossDefeatService(relics2)
    awarded_again = svc2.on_boss_defeated(event)
    assert awarded_again is False, "Final relic should not be awarded twice"
    assert relics2.collected_count() == prev_count


def test_collection_view_reflects_final_relic_state(tmp_path: Path):
    save = SaveService(str(tmp_path), namespace="ui_player")
    defs = RelicDefinitions()
    relics = RelicManager(save, defs)
    view = RelicCollectionView(relics)

    # Initially not collected
    assert view.is_final_relic_collected() is False

    # Award via service
    svc = BossDefeatService(relics)
    event = BossDefeatedEvent(floor=99, boss_id="final_boss", is_final=True, run_id="run-ui")
    svc.on_boss_defeated(event)

    # UI should now reflect collection
    assert view.is_final_relic_collected() is True

    # Ensure there is exactly one final relic item and it's collected
    finals = [i for i in view.items() if i.category == "final"]
    assert len(finals) == 1
    assert finals[0].id == defs.final_relic_id()
    assert finals[0].collected is True
