Debugging, Telemetry & QA Guide

Overview
This guide explains how to use the debug overlay, seed controls, telemetry logging, and the QA determinism harness.

Configuration
- AMOR_DEBUG=1 enables debug mode.
- AMOR_DEBUG_OVERLAY=1 starts the overlay visible.
- AMOR_TELEMETRY=1 enables telemetry logging (default).
- AMOR_TELEMETRY_DIR sets telemetry output directory.
- AMOR_TELEMETRY_FLUSH_SIZE sets buffer size before flush (default 50).
- AMOR_SEED sets the global seed (int); string seeds can be set programmatically.

Seed Controls
- Use SeedManager to set and control the RNG used across systems. Avoid using Python's global random.
  from amor.core.seed import SeedManager
  sm = SeedManager()
  sm.set_seed(12345)
  x = sm.randint(1, 10)
  with sm.temporary_seed("floor-42"):
      # Deterministic block
      ...

Telemetry
- Use TelemetryClient to emit JSON-lines events; they are buffered and flushed to disk.
  from amor.telemetry import TelemetryClient
  tc = TelemetryClient(enabled=True)
  tc.set_global_context(player_id="anon", session_type="local")
  tc.emit("game_start")
  tc.emit("enter_floor", depth=12)
  tc.flush()

Debug Overlay
- The DebugOverlay is headless-friendly. It produces text lines and can render with Arcade if installed.
  from amor.debug import DebugOverlay
  from amor.config import AppConfig
  cfg = AppConfig.from_env()
  overlay = DebugOverlay(cfg, seed_manager=sm, telemetry=tc)
  print(overlay.to_text())
- In an Arcade window, call overlay.draw(x, y) in your on_draw handler and overlay.toggle() on a key press.

QA Determinism Harness
- Record RNG-driven operations and create a trace that can be verified later.
  from amor.qa import QAHarness
  qa = QAHarness(sm)
  qa.randint(1, 10)
  qa.choice(["sword", "shield", "potion"])
  trace = qa.snapshot()
  ok, info = qa.reproduce(trace)
  assert ok
- Store trace.to_json() in fixtures for regression tests.

Best Practices
- Inject SeedManager into systems (map gen, loot, combat) to ensure determinism.
- Emit telemetry events for major milestones (start, floor enter/exit, boss fights, deaths).
- Keep the overlay minimal in release builds; guard on config.debug_enabled.
