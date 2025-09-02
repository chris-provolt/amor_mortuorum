from __future__ import annotations

import json
from pathlib import Path

import pytest

from amormortuorum.settings import GameSettings, SettingsManager, SettingsRuntimeAdapter


class FakeAdapter(SettingsRuntimeAdapter):
    def __init__(self):
        super().__init__()
        self.calls = []

    def set_master_volume(self, volume: float) -> None:
        self.calls.append(("master", round(volume, 3)))

    def set_music_volume(self, volume: float) -> None:
        self.calls.append(("music", round(volume, 3)))

    def set_sfx_volume(self, volume: float) -> None:
        self.calls.append(("sfx", round(volume, 3)))

    def set_muted(self, muted: bool) -> None:
        self.calls.append(("muted", muted))

    def set_fullscreen(self, fullscreen: bool) -> None:
        self.calls.append(("fullscreen", fullscreen))

    def set_vsync(self, vsync: bool) -> None:
        self.calls.append(("vsync", vsync))

    def set_resolution(self, resolution: str) -> None:
        self.calls.append(("resolution", resolution))

    def apply_all(self, settings: GameSettings) -> None:
        super().apply_all(settings)


@pytest.fixture()
def tmp_config_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cfg"
    d.mkdir()
    return d


def test_settings_persist_and_apply(tmp_config_dir: Path):
    adapter = FakeAdapter()
    mgr = SettingsManager(config_dir=tmp_config_dir, runtime_adapter=adapter)

    # Defaults applied on init via load/save
    # change and ensure clamping + adapter calls
    calls_before = len(adapter.calls)
    notified = []
    mgr.subscribe(lambda s: notified.append(s))

    mgr.set_audio(master_volume=1.5, music_volume=-0.1, sfx_volume=0.42)
    # Clamped values
    assert mgr.settings.audio.master_volume == 1.0
    assert mgr.settings.audio.music_volume == 0.0
    assert mgr.settings.audio.sfx_volume == 0.42

    # Adapter must have been called for each change
    assert ("master", 1.0) in adapter.calls
    assert ("music", 0.0) in adapter.calls
    assert ("sfx", 0.42) in adapter.calls
    assert len(notified) >= 1

    mgr.set_video(fullscreen=True, vsync=False, resolution="1600x900")
    assert ("fullscreen", True) in adapter.calls
    assert ("vsync", False) in adapter.calls
    assert ("resolution", "1600x900") in adapter.calls

    # Save file exists and contains expected keys
    settings_file = tmp_config_dir / "settings.json"
    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert set(data.keys()) == {"audio", "video", "controls"}

    # Reload and ensure values persisted
    mgr2 = SettingsManager(config_dir=tmp_config_dir, runtime_adapter=FakeAdapter())
    assert mgr2.settings.audio.sfx_volume == pytest.approx(0.42)
    assert mgr2.settings.video.fullscreen is True
    assert mgr2.settings.video.vsync is False
    assert mgr2.settings.video.resolution == "1600x900"


def test_set_control_validation(tmp_config_dir: Path):
    mgr = SettingsManager(config_dir=tmp_config_dir, runtime_adapter=FakeAdapter())
    mgr.set_control("move_up", "UP")
    assert mgr.settings.controls.move_up == "UP"
    with pytest.raises(ValueError):
        mgr.set_control("invalid_action", "X")


def test_apply_all_respects_muted(tmp_config_dir: Path):
    adapter = FakeAdapter()
    mgr = SettingsManager(config_dir=tmp_config_dir, runtime_adapter=adapter)
    mgr.set_audio(muted=True)
    adapter.calls.clear()
    mgr.apply()
    # When muted, apply_all should call muted path (we test that apply_all drives volumes indirectly)
    # Since FakeAdapter.set_muted not called by apply_all (only set by set_audio), we ensure master volume not applied when muted
    # We simulate by ensuring no volume calls after apply when muted
    assert not any(c for c in adapter.calls if c[0] in ("master", "music", "sfx"))
