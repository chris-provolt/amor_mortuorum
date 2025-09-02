from __future__ import annotations

from amor_mortuorum.engine.loop import GameEngine, GameConfig


def test_engine_runs_exact_steps():
    engine = GameEngine(GameConfig(tick_rate=0, max_steps=5))
    engine.run()
    assert engine.step == 5
    assert engine.running is False


def test_engine_update_and_stop():
    engine = GameEngine(GameConfig(tick_rate=0, max_steps=2))
    engine.start()
    engine.update(0.016)
    engine.update(0.016)
    assert engine.step == 2
    assert engine.running is False
