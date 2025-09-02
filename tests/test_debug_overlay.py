import math

import pytest

from amor.debug.overlay import DebugOverlay, GameTelemetry, FPSCounter


def test_toggle_with_f3_key(monkeypatch):
    # Simulate arcade.key.F3 without importing arcade in environments lacking GL
    class DummyArcade:
        class key:
            F3 = 114  # arbitrary unique code

    # Patch module arcade in overlay to our dummy
    import amor.debug.overlay as overlay_mod

    original_arcade = overlay_mod.arcade
    overlay_mod.arcade = DummyArcade
    try:
        overlay = DebugOverlay(enabled=False)
        assert not overlay.enabled
        overlay.on_key_press(DummyArcade.key.F3, 0)
        assert overlay.enabled
        overlay.on_key_press(DummyArcade.key.F3, 0)
        assert not overlay.enabled
    finally:
        overlay_mod.arcade = original_arcade


def test_compose_lines_contains_expected_fields():
    tel = GameTelemetry(seed=123456789, floor=7)
    tel.update_entities({"mobs": 5, "items": 3, "projectiles": 2})
    tel.set_extra("Room", "BSP-23")
    overlay = DebugOverlay(telemetry=tel, enabled=True)

    # Simulate a couple frames to get non-zero FPS
    overlay.on_update(0.016)
    overlay.on_update(0.016)

    lines = overlay.compose_lines()

    assert any(line.startswith("FPS:") for line in lines)
    assert any("Seed:" in line and "123456789" in line for line in lines)
    assert any("Floor:" in line and "7" in line for line in lines)
    ent_line = next(line for line in lines if line.startswith("Entities:"))
    assert "total=10" in ent_line
    assert "items=3" in ent_line and "mobs=5" in ent_line and "projectiles=2" in ent_line
    assert any(line.startswith("Room:") and "BSP-23" in line for line in lines)


def test_compose_lines_when_missing_values():
    overlay = DebugOverlay(telemetry=GameTelemetry(), enabled=True)
    lines = overlay.compose_lines()
    # Default placeholders
    assert any("Seed:" in line and "-" in line for line in lines)
    assert any("Floor:" in line and "-" in line for line in lines)
    assert any(line.strip() == "Entities: -" for line in lines)


def test_fps_counter_accuracy():
    fps = FPSCounter(time_window=1.0)

    # 60 FPS simulation for ~1 second
    for _ in range(60):
        fps.update(1.0 / 60.0)
    assert 55.0 <= fps.fps <= 65.0

    # 30 FPS simulation
    fps.reset()
    for _ in range(30):
        fps.update(1.0 / 30.0)
    assert 25.0 <= fps.fps <= 35.0

    # dt zero should not blow up
    before = fps.fps
    fps.update(0.0)
    assert fps.fps == before


def test_overlay_line_cache_invalidation():
    tel = GameTelemetry(seed=1, floor=1)
    overlay = DebugOverlay(telemetry=tel, enabled=True)

    # Initial compose
    lines1 = overlay.compose_lines()

    # After on_update, FPS changed, lines should be recomposed (cache invalidated)
    overlay.on_update(0.5)
    lines2 = overlay.compose_lines()

    # We can't guarantee visual diff, but lists should be separate objects and not crash
    assert lines1 is not lines2


