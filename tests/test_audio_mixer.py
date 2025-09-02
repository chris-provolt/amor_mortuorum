import math

from src.audio.engine import FakeAudioEngine
from src.audio.mixer import AudioMixer


def advance(mixer: AudioMixer, seconds: float, step: float = 0.05):
    t = 0.0
    while t < seconds:
        mixer.tick(step)
        t += step


def test_fade_in_and_out_linear_and_monotonic():
    engine = FakeAudioEngine()
    track = engine.load_track("layer")

    mixer = AudioMixer()
    mixer.register_track("layer", track)

    # Start at 0 volume, fade to 1.0 over 1s
    mixer.set_volume("layer", 0.0)
    mixer.fade_to("layer", 1.0, 1.0)

    last = track.get_volume()
    deltas = []
    for _ in range(20):  # 1.0s total at 0.05 steps
        mixer.tick(0.05)
        v = track.get_volume()
        assert v >= last - 1e-6  # monotonic increase
        deltas.append(v - last)
        last = v

    assert math.isclose(track.get_volume(), 1.0, abs_tol=1e-3)

    # Deliberately check no step creates a sudden pop (> 0.2 is considered abrupt for 50ms frames)
    assert max(deltas) <= 0.2

    # Now fade out smoothly to zero and ensure the player stops
    mixer.fade_to("layer", 0.0, 1.0, stop_at_zero=True)
    advance(mixer, 1.0)

    assert math.isclose(track.get_volume(), 0.0, abs_tol=1e-3)
    assert track.is_playing() is False


def test_replacing_fade_uses_current_volume():
    engine = FakeAudioEngine()
    track = engine.load_track("layer")
    mixer = AudioMixer()
    mixer.register_track("layer", track)

    mixer.set_volume("layer", 0.0)
    mixer.fade_to("layer", 1.0, 1.0)

    # Advance halfway then change target; new fade should start from current vol
    mixer.tick(0.5)
    mid_vol = track.get_volume()

    mixer.fade_to("layer", 0.5, 0.5)  # new fade
    mixer.tick(0.25)
    # 50% progress towards 0.5 from mid_vol
    expected = mid_vol + 0.5 * (0.5 - mid_vol)
    assert math.isclose(track.get_volume(), expected, abs_tol=1e-3)


def test_immediate_fade_sets_volume_and_stops():
    engine = FakeAudioEngine()
    track = engine.load_track("layer")
    mixer = AudioMixer()
    mixer.register_track("layer", track)

    mixer.play("layer", volume=0.3)
    assert track.is_playing() is True

    mixer.fade_to("layer", 0.0, 0.0, stop_at_zero=True)
    assert track.get_volume() == 0.0
    assert track.is_playing() is False
