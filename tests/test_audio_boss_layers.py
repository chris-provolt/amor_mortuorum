import math

from src.audio.boss_layers import BossLayerConfig, BossLayerController
from src.audio.engine import FakeAudioEngine
from src.audio.mixer import AudioMixer


def advance(mixer: AudioMixer, seconds: float, step: float = 0.05):
    t = 0.0
    while t < seconds:
        mixer.tick(step)
        t += step


def test_miniboss_layer_fades_in_and_out_without_clicks():
    engine = FakeAudioEngine()
    mini = engine.load_track("miniboss_overlay")

    mixer = AudioMixer()
    mixer.register_track("miniboss_overlay", mini)

    cfg = BossLayerConfig(miniboss_volume=0.8, fade_in_seconds=1.0, fade_out_seconds=1.0)
    ctl = BossLayerController(mixer, config=cfg)

    ctl.enter_miniboss()

    # simulate fade-in
    last = mini.get_volume()
    max_delta = 0.0
    for _ in range(20):  # 1.0s total
        mixer.tick(0.05)
        v = mini.get_volume()
        assert v >= last - 1e-6
        max_delta = max(max_delta, v - last)
        last = v

    assert math.isclose(mini.get_volume(), 0.8, abs_tol=1e-3)
    assert mini.is_playing() is True
    # No abrupt step that would cause a click/pop at 50ms frames
    assert max_delta <= 0.2

    ctl.exit_miniboss()
    advance(mixer, 1.0)

    assert math.isclose(mini.get_volume(), 0.0, abs_tol=1e-3)
    assert mini.is_playing() is False


def test_escalate_miniboss_to_final_crossfades_layers():
    engine = FakeAudioEngine()
    mini = engine.load_track("miniboss_overlay")
    final = engine.load_track("final_boss_overlay")

    mixer = AudioMixer()
    mixer.register_track("miniboss_overlay", mini)
    mixer.register_track("final_boss_overlay", final)

    cfg = BossLayerConfig(miniboss_volume=0.7, final_boss_volume=0.9, fade_in_seconds=1.0, fade_out_seconds=1.0)
    ctl = BossLayerController(mixer, config=cfg)

    ctl.enter_miniboss()
    advance(mixer, 1.0)
    assert math.isclose(mini.get_volume(), 0.7, abs_tol=1e-3)

    # Escalate to final
    ctl.escalate_miniboss_to_final()

    # half way through crossfade: mini decreasing, final increasing
    advance(mixer, 0.5)
    assert mini.get_volume() < 0.7
    assert final.get_volume() > 0.0

    # complete
    advance(mixer, 0.5)
    assert math.isclose(final.get_volume(), 0.9, abs_tol=1e-3)
    assert math.isclose(mini.get_volume(), 0.0, abs_tol=1e-3)
    assert mini.is_playing() is False


def test_idempotent_enter_calls_do_not_stack():
    engine = FakeAudioEngine()
    mini = engine.load_track("miniboss_overlay")
    final = engine.load_track("final_boss_overlay")

    mixer = AudioMixer()
    mixer.register_track("miniboss_overlay", mini)
    mixer.register_track("final_boss_overlay", final)

    ctl = BossLayerController(mixer)

    ctl.enter_miniboss()
    # Call again; should not create errors or duplicate tasks
    ctl.enter_miniboss()

    # advance a bit
    mixer.tick(0.5)
    v = mini.get_volume()
    # entering again shouldn't have decreased volume
    assert v > 0.0

    ctl.enter_final_boss()
    # call again
    ctl.enter_final_boss()
    advance(mixer, 1.5)
    assert final.get_volume() > 0.0
