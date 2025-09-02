from amor.config import AppConfig
from amor.core.seed import SeedManager
from amor.debug import DebugOverlay
from amor.telemetry import TelemetryClient


def test_overlay_lines_contains_key_info(tmp_path):
    cfg = AppConfig.from_env()
    cfg.build_version = "test-build"
    sm = SeedManager(123)
    tc = TelemetryClient(enabled=True, out_dir=tmp_path)

    fps = lambda: 60.0
    ft = lambda: 16.66

    overlay = DebugOverlay(cfg, seed_manager=sm, telemetry=tc, providers=None)
    # override providers after init
    overlay.providers.fps = fps
    overlay.providers.frame_time_ms = ft

    lines = overlay.lines()
    joined = "\n".join(lines)

    assert "Amor Mortuorum" in joined
    assert "Build: test-build" in joined
    assert "Seed: 123" in joined
    assert "FPS: 60.0" in joined
    assert "Frame: 16.66" in joined
    assert "Telemetry: ON" in joined


def test_overlay_toggle_visibility(tmp_path):
    cfg = AppConfig.from_env()
    sm = SeedManager(1)
    tc = TelemetryClient(enabled=False, out_dir=tmp_path)
    overlay = DebugOverlay(cfg, seed_manager=sm, telemetry=tc)
    v0 = overlay.visible
    overlay.toggle()
    assert overlay.visible != v0
