import json
from pathlib import Path

from amor.telemetry import TelemetryClient


def test_telemetry_emit_and_flush(tmp_path: Path):
    out = tmp_path / "tel"
    tc = TelemetryClient(enabled=True, out_dir=out, app_name="TestApp", build_version="1.2.3", flush_size=10)
    tc.set_global_context(player="alice", session_type="local")

    tc.emit("game_start")
    tc.emit("enter_floor", depth=5)
    tc.flush()

    assert tc.output_file.exists()
    lines = tc.output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    ev1 = json.loads(lines[0])
    ev2 = json.loads(lines[1])
    assert ev1["event"] == "game_start"
    assert ev1["attrs"]["app"] == "TestApp"
    assert ev1["attrs"]["build"] == "1.2.3"
    assert ev1["attrs"]["player"] == "alice"

    assert ev2["event"] == "enter_floor"
    assert ev2["attrs"]["depth"] == 5
    assert ev2["seq"] == 2


def test_telemetry_disabled_no_output(tmp_path: Path):
    out = tmp_path / "tel"
    tc = TelemetryClient(enabled=False, out_dir=out)
    tc.emit("x")
    tc.flush()
    # No file is created when disabled
    assert not tc.output_file.exists()
