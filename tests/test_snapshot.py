from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from amor.models.run_state import Character, Party, RunState
from amor.save.snapshot import (
    SnapshotIntegrityError,
    SnapshotManager,
    SnapshotError,
)


class TempSnapshotEnv:
    def __init__(self, tmp_path: Path) -> None:
        self.base_dir = tmp_path / "appdata"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.mgr = SnapshotManager(base_dir=self.base_dir)


def sample_run_state(floor: int = 3, seed: int = 1234) -> RunState:
    party = Party(
        members=[
            Character(name="Aerin", level=4, hp=28, max_hp=30),
            Character(name="Bran", level=4, hp=35, max_hp=35),
        ]
    )
    return RunState(floor=floor, dungeon_seed=seed, party=party)


def test_save_and_load_consumes_snapshot(tmp_path: Path) -> None:
    env = TempSnapshotEnv(tmp_path)
    rs = sample_run_state(floor=7, seed=2025)
    rng = random.Random(99)

    env.mgr.save_snapshot(rs, rng)
    assert env.mgr.has_snapshot() is True

    loaded_rs, loaded_rng = env.mgr.load_snapshot()

    assert env.mgr.has_snapshot() is False  # consumed on load
    assert loaded_rs.floor == 7
    assert loaded_rs.dungeon_seed == 2025
    assert [m.name for m in loaded_rs.party.members] == ["Aerin", "Bran"]
    # RNG produces a known next value after load
    v = loaded_rng.random()
    assert isinstance(v, float)


def test_overwrite_single_slot(tmp_path: Path) -> None:
    env = TempSnapshotEnv(tmp_path)
    rng = random.Random(123)

    env.mgr.save_snapshot(sample_run_state(floor=2, seed=111), rng)
    env.mgr.save_snapshot(sample_run_state(floor=5, seed=222), rng)

    rs2, _ = env.mgr.load_snapshot()
    assert rs2.floor == 5
    assert rs2.dungeon_seed == 222


def test_hmac_integrity_rejects_tampering(tmp_path: Path) -> None:
    env = TempSnapshotEnv(tmp_path)
    rs = sample_run_state(floor=9, seed=909)
    rng = random.Random(77)

    env.mgr.save_snapshot(rs, rng)
    # Tamper: change floor without updating HMAC
    path = env.mgr.snapshot_path
    data = json.loads(path.read_text())
    data["run_state"]["floor"] = 99
    path.write_text(json.dumps(data))

    with pytest.raises(SnapshotIntegrityError):
        env.mgr.load_snapshot()

    # Snapshot cleared after failure
    assert env.mgr.has_snapshot() is False


def test_rng_state_restored(tmp_path: Path) -> None:
    env = TempSnapshotEnv(tmp_path)
    rng1 = random.Random(42)

    # Advance RNG some steps to simulate gameplay
    _ = [rng1.random() for _ in range(5)]

    rs = sample_run_state(floor=10, seed=4242)
    env.mgr.save_snapshot(rs, rng1)

    # Expected continuation sequence if we had continued from rng1
    rng_expected = random.Random(42)
    _ = [rng_expected.random() for _ in range(5)]

    # Load snapshot and compare next values
    _, rng_loaded = env.mgr.load_snapshot()

    next_vals_loaded = [rng_loaded.random() for _ in range(3)]
    next_vals_expected = [rng_expected.random() for _ in range(3)]

    assert next_vals_loaded == next_vals_expected


def test_load_without_snapshot_raises(tmp_path: Path) -> None:
    env = TempSnapshotEnv(tmp_path)
    with pytest.raises(SnapshotError):
        env.mgr.load_snapshot()
