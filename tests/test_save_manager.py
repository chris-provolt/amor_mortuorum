from __future__ import annotations

from pathlib import Path

import pytest

from amormortuorum.save_system import SaveManager


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


def test_snapshot_lifecycle(tmp_data_dir: Path):
    sm = SaveManager(data_dir=tmp_data_dir)
    assert not sm.has_snapshot()

    data = {"floor": 1, "hp": 25, "inventory": ["potion"]}
    sm.create_snapshot(data)
    assert sm.has_snapshot()

    loaded = sm.load_snapshot()
    assert loaded["floor"] == 1
    assert loaded["inventory"] == ["potion"]

    sm.delete_snapshot()
    assert not sm.has_snapshot()


def test_load_snapshot_errors(tmp_data_dir: Path):
    sm = SaveManager(data_dir=tmp_data_dir)
    with pytest.raises(FileNotFoundError):
        sm.load_snapshot()

    # Write invalid JSON
    f = sm.snapshot_file
    f.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        sm.load_snapshot()
