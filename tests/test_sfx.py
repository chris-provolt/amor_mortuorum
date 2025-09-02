import json
import os
from pathlib import Path

import pytest

from amormortuorum.audio.sfx import SFXEvent, SFXManager


class FakeSound:
    def __init__(self):
        self.calls = []

    def play(self, volume=1.0):
        self.calls.append(volume)


class FakeBackend:
    class Sound:
        def __init__(self, path, streaming=False):
            # Pretend to load anything; in tests we won't hit this normally
            self._path = path
            self._streaming = streaming
            self._calls = []

        def play(self, volume=1.0):
            self._calls.append(volume)


def test_register_and_play_with_fake_sound():
    mgr = SFXManager(auto_load=False)
    snd = FakeSound()
    mgr.register_sound(SFXEvent.UI_CLICK, snd)

    ok = mgr.play(SFXEvent.UI_CLICK)

    assert ok is True
    assert len(snd.calls) == 1
    assert 0.0 <= snd.calls[0] <= 1.0


def test_play_returns_false_when_unregistered():
    mgr = SFXManager(auto_load=False)
    assert mgr.play(SFXEvent.CHEST_OPEN) is False


def test_missing_config_file_is_graceful(tmp_path: Path):
    cfg_path = tmp_path / "nope.json"
    mgr = SFXManager(config_path=str(cfg_path), auto_load=True)
    # No exception; nothing registered
    assert mgr.play(SFXEvent.HIT) is False


def test_missing_assets_do_not_crash(tmp_path: Path):
    # Write config pointing to non-existent files
    cfg = {
        "ui_click": str(tmp_path / "missing_ui_click.wav"),
        "chest_open": str(tmp_path / "missing_chest.wav"),
        "hit": str(tmp_path / "missing_hit.wav"),
        "defeat": str(tmp_path / "missing_defeat.wav"),
    }
    cfg_path = tmp_path / "sfx.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    mgr = SFXManager(config_path=str(cfg_path), auto_load=True, backend=FakeBackend)
    # All plays should return False and not raise
    assert mgr.play(SFXEvent.UI_CLICK) is False
    assert mgr.play(SFXEvent.CHEST_OPEN) is False
    assert mgr.play(SFXEvent.HIT) is False
    assert mgr.play(SFXEvent.DEFEAT) is False


def test_enabled_flag_controls_playback():
    mgr = SFXManager(auto_load=False)
    snd = FakeSound()
    mgr.register_sound(SFXEvent.HIT, snd)

    mgr.enabled = False
    assert mgr.play(SFXEvent.HIT) is False
    assert snd.calls == []

    mgr.enabled = True
    assert mgr.play(SFXEvent.HIT) is True
    assert len(snd.calls) == 1


def test_volume_is_clamped():
    mgr = SFXManager(auto_load=False)
    snd = FakeSound()
    mgr.register_sound(SFXEvent.DEFEAT, snd)

    mgr.volume = 5.0
    assert mgr.volume == 1.0
    mgr.play(SFXEvent.DEFEAT)
    assert snd.calls[-1] == pytest.approx(1.0)

    mgr.volume = -0.5
    assert mgr.volume == 0.0
    mgr.play(SFXEvent.DEFEAT)
    assert snd.calls[-1] == pytest.approx(0.0)


def test_register_path_works_when_file_exists(tmp_path: Path):
    # Create a fake file to represent an audio asset
    sound_file = tmp_path / "click.wav"
    sound_file.write_bytes(b"FAKE")

    mgr = SFXManager(auto_load=False, backend=FakeBackend)
    mgr.register_path(SFXEvent.UI_CLICK, str(sound_file))

    # Since FakeBackend loads any path that exists, playback should succeed
    assert mgr.play(SFXEvent.UI_CLICK) is True


def test_reload_reads_config_and_registers(tmp_path: Path):
    sound_file = tmp_path / "hit.wav"
    sound_file.write_bytes(b"FAKE")

    cfg = {"hit": str(sound_file)}
    cfg_path = tmp_path / "sfx.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    mgr = SFXManager(config_path=str(cfg_path), auto_load=True, backend=FakeBackend)

    assert mgr.play(SFXEvent.HIT) is True

    # Update config to point to a different file
    sound_file2 = tmp_path / "hit2.wav"
    sound_file2.write_bytes(b"FAKE2")
    cfg = {"hit": str(sound_file2)}
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    mgr.reload()

    assert mgr.play(SFXEvent.HIT) is True
