import json
from pathlib import Path

import pytest

from src.core.save_system import SaveSystem, CRYPT_CAPACITY


def test_default_meta_creation(tmp_path: Path):
    save_dir = tmp_path / "saves"
    ss = SaveSystem(save_dir=save_dir)
    meta = ss.load_meta()

    assert meta.crypt == []
    assert meta.relics_found == set()

    meta_path = save_dir / "meta.json"
    assert meta_path.exists()

    # Ensure JSON is valid and has expected keys
    with meta_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["crypt"] == []
    assert data["relics_found"] == []
    assert data.get("version") == 1


def test_crypt_persists_across_restarts(tmp_path: Path):
    save_dir = tmp_path / "saves"

    ss1 = SaveSystem(save_dir=save_dir)
    ss1.set_crypt(["potion_minor", "scroll_fire"])  # auto-persists

    # Simulate restart with a new instance
    ss2 = SaveSystem(save_dir=save_dir)
    meta2 = ss2.load_meta()

    assert meta2.crypt == ["potion_minor", "scroll_fire"]


def test_relics_persist_across_restarts(tmp_path: Path):
    save_dir = tmp_path / "saves"

    ss1 = SaveSystem(save_dir=save_dir)
    ss1.add_relic("relic_1")
    ss1.add_relic("relic_final")

    ss2 = SaveSystem(save_dir=save_dir)
    meta2 = ss2.load_meta()

    assert meta2.relics_found == {"relic_1", "relic_final"}


def test_corrupt_json_resets_defaults(tmp_path: Path):
    save_dir = tmp_path / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    meta_path = save_dir / "meta.json"

    # Write invalid JSON
    meta_path.write_text("{ not valid JSON", encoding="utf-8")

    ss = SaveSystem(save_dir=save_dir)
    meta = ss.load_meta()

    assert meta.crypt == []
    assert meta.relics_found == set()

    # File should be replaced with valid defaults
    with meta_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"version": 1, "crypt": [], "relics_found": []}


def test_invalid_schema_resets_defaults(tmp_path: Path):
    save_dir = tmp_path / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    meta_path = save_dir / "meta.json"

    # Write valid JSON but wrong types
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump({"version": 1, "crypt": "not a list", "relics_found": 42}, f)

    ss = SaveSystem(save_dir=save_dir)
    meta = ss.load_meta()

    assert meta.crypt == []
    assert meta.relics_found == set()

    # File should be replaced with valid defaults
    with meta_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"version": 1, "crypt": [], "relics_found": []}


def test_crypt_capacity_enforced(tmp_path: Path):
    save_dir = tmp_path / "saves"
    ss = SaveSystem(save_dir=save_dir)

    # Fill up to capacity
    for i in range(CRYPT_CAPACITY):
        added = ss.add_to_crypt(f"item_{i}")
        assert added is True
    # Adding beyond capacity should fail
    assert ss.add_to_crypt("overflow_item") is False

    meta = ss.load_meta()
    assert len(meta.crypt) == CRYPT_CAPACITY
