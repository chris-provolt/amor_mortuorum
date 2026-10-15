"""Keeps the balance simulator importable and sane (small, fast runs)."""
from amormortuorum.data import GameData
from tools.balance.simulate import simulate_run, summarize


def test_simulator_runs_and_summarizes():
    data = GameData.load()
    results = [simulate_run(seed, data, party_size=2) for seed in (1, 2, 3, 4)]
    summary = summarize(results)
    assert summary["runs"] == 4
    assert 1 <= summary["min_floor"] <= summary["max_floor"] <= 99
    assert set(summary["boss_kills"]) == {20, 40, 60, 80, 99}
    for r in results:
        assert r.cause in ("died", "victory")
        assert r.battles > 0 and r.level >= 1
