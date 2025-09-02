import json
import os
from pathlib import Path
import sys

import pytest

# Ensure src is importable when tests are run locally
ROOT = Path(__file__).resolve().parents[1]
src_path = ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from amormortuorum.persistence import (
    SaveManager,
    SavePolicy,
    MetaState,
    RunState,
    SaveGame,
    Item,
    RelicCollection,
    SaveNotAllowed,
    SaveValidationError,
    CorruptSaveError,
)


def test_crypt_capacity_and_persistence(tmp_path: Path):
    mgr = SaveManager(root_dir=tmp_path, profile_id="test")
    meta = MetaState()
    # Add up to 3 items
    meta.crypt.add_item(Item(id="potion_minor", name="Minor Potion", qty=2))
    meta.crypt.add_item(Item(id="scroll_fire", name="Scroll of Fire", qty=1))
    meta.crypt.add_item(Item(id="amulet_luck", name="Amulet of Luck", qty=1))

    # Fourth should fail
    with pytest.raises(SaveValidationError):
        meta.crypt.add_item(Item(id="bomb_small", name="Small Bomb", qty=1))

    mgr.save_meta(meta)

    loaded_meta = mgr.load_meta()
    assert len(loaded_meta.crypt.items) == 3
    assert loaded_meta.crypt.items[0].id == "potion_minor"


def test_relic_collection_validation():
    rc = RelicCollection()
    rc.add("veil_fragment_1")
    assert rc.has("veil_fragment_1")

    with pytest.raises(SaveValidationError):
        rc.add("unknown_relic")


def test_graveyard_only_full_save(tmp_path: Path):
    mgr = SaveManager(root_dir=tmp_path, profile_id="test2")
    # Start in dungeon (not in graveyard)
    run = RunState(floor=3, in_graveyard=False, rng_seed=42)
    save = SaveGame(meta=MetaState(), run=run, profile_id="test2")

    # Attempting to save should fail by default policy
    with pytest.raises(SaveNotAllowed):
        mgr.save_full(save)

    # Move to graveyard -> allow save
    save.run.in_graveyard = True
    mgr.save_full(save)

    loaded = mgr.load_full()
    assert loaded.run is not None
    assert loaded.run.floor == 3
    assert loaded.meta.crypt.items == []


def test_save_and_quit_flag_allows_midrun_save(tmp_path: Path):
    mgr = SaveManager(root_dir=tmp_path, profile_id="test3", policy=SavePolicy(allow_save_and_quit=True))
    run = RunState(floor=10, in_graveyard=False, rng_seed=99)
    save = SaveGame(meta=MetaState(), run=run, profile_id="test3")
    # Should not raise now
    mgr.save_full(save)
    loaded = mgr.load_full()
    assert loaded.run is not None and loaded.run.floor == 10


def test_atomic_write_and_backup_recovery(tmp_path: Path):
    mgr = SaveManager(root_dir=tmp_path, profile_id="test4")

    # Create a valid save at graveyard
    save = SaveGame(meta=MetaState(), run=RunState(floor=1, in_graveyard=True, rng_seed=1), profile_id="test4")
    mgr.save_full(save)

    run_path = mgr.run_path
    bak_path = run_path.with_suffix(run_path.suffix + ".bak")

    assert run_path.exists()

    # Corrupt the primary save file intentionally
    run_path.write_text("{ this is not valid json ")

    # Ensure backup exists from atomic write
    assert bak_path.exists()

    # Loading should recover from backup
    loaded = mgr.load_full()
    assert loaded.run is not None
    assert loaded.run.floor == 1


def test_corruption_without_backup_raises(tmp_path: Path):
    mgr = SaveManager(root_dir=tmp_path, profile_id="test5")

    # Save meta to create files
    meta = MetaState()
    mgr.save_meta(meta)

    # Deliberately corrupt both primary and backup
    mgr.meta_path.write_text("not json")
    bak = mgr.meta_path.with_suffix(mgr.meta_path.suffix + ".bak")
    if bak.exists():
        bak.write_text("also not json")
    # Remove run file to force failure
    if mgr.run_path.exists():
        mgr.run_path.unlink()

    with pytest.raises(CorruptSaveError):
        mgr.load_meta()
