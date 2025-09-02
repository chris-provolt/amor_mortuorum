from __future__ import annotations

import os
from pathlib import Path

import io
import textwrap

import pytest

from game.settings import (
    SETTINGS,
    Settings,
    TOPIC_ALL,
    TOPIC_AUDIO,
    TOPIC_UI,
    TOPIC_WINDOW,
)


class DummyWindow:
    def __init__(self) -> None:
        self.fullscreen = False
        self.vsync = False
        self.width = 0
        self.height = 0
        self.calls = []

    def set_fullscreen(self, value: bool) -> None:
        self.calls.append(("set_fullscreen", value))
        self.fullscreen = bool(value)

    def set_vsync(self, value: bool) -> None:
        self.calls.append(("set_vsync", value))
        self.vsync = bool(value)

    def set_size(self, w: int, h: int) -> None:
        self.calls.append(("set_size", w, h))
        self.width = int(w)
        self.height = int(h)


class DummyAudio:
    def __init__(self) -> None:
        self.master = None
        self.music = None
        self.sfx = None
        self.calls = []

    def set_master_volume(self, v: float) -> None:
        self.calls.append(("set_master_volume", v))
        self.master = v

    def set_music_volume(self, v: float) -> None:
        self.calls.append(("set_music_volume", v))
        self.music = v

    def set_sfx_volume(self, v: float) -> None:
        self.calls.append(("set_sfx_volume", v))
        self.sfx = v


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AM_FULLSCREEN", "1")
    monkeypatch.setenv("AM_VSYNC", "false")
    monkeypatch.setenv("AM_WIDTH", "1920")
    monkeypatch.setenv("AM_HEIGHT", "1080")
    monkeypatch.setenv("AM_MASTER_VOLUME", "0.5")
    monkeypatch.setenv("AM_MUSIC_VOLUME", "0.4")
    monkeypatch.setenv("AM_SFX_VOLUME", "0.3")
    monkeypatch.setenv("AM_SHOW_MINIMAP", "no")
    monkeypatch.setenv("AM_FOG_OF_WAR", "off")

    settings = Settings.from_sources()

    assert settings.fullscreen is True
    assert settings.vsync is False
    assert settings.width == 1920
    assert settings.height == 1080
    assert settings.master_volume == 0.5
    assert settings.music_volume == 0.4
    assert settings.sfx_volume == 0.3
    assert settings.show_minimap is False
    assert settings.fog_of_war is False


def test_file_overrides(tmp_path: Path) -> None:
    toml_content = textwrap.dedent(
        """
        [window]
        width = 1024
        height = 768
        fullscreen = true
        vsync = true

        [audio]
        master_volume = 0.9
        music_volume = 0.6
        sfx_volume = 0.2

        [ui]
        show_minimap = false
        fog_of_war = false
        """
    )
    fp = tmp_path / "settings.toml"
    fp.write_text(toml_content, encoding="utf-8")

    settings = Settings.from_sources(file_path=fp)

    assert settings.width == 1024
    assert settings.height == 768
    assert settings.fullscreen is True
    assert settings.vsync is True
    assert settings.master_volume == 0.9
    assert settings.music_volume == 0.6
    assert settings.sfx_volume == 0.2
    assert pytest.approx(settings.effective_music_volume, 1e-6) == 0.54
    assert pytest.approx(settings.effective_sfx_volume, 1e-6) == 0.18
    assert settings.show_minimap is False
    assert settings.fog_of_war is False


def test_apply_to_window() -> None:
    s = Settings.from_sources()
    s.update(width=1600, height=900, fullscreen=True, vsync=False)

    win = DummyWindow()
    s.apply_to_window(win)

    assert win.fullscreen is True
    assert win.vsync is False
    assert win.width == 1600
    assert win.height == 900
    # Ensure the appropriate methods were called at least once
    method_names = [c[0] for c in win.calls]
    assert "set_fullscreen" in method_names
    assert "set_vsync" in method_names
    assert "set_size" in method_names


def test_apply_to_audio_and_observers() -> None:
    s = Settings.from_sources()

    # Track observer notifications
    notifications = {TOPIC_AUDIO: 0, TOPIC_WINDOW: 0, TOPIC_UI: 0, TOPIC_ALL: 0}

    def on_audio(_settings: Settings) -> None:
        notifications[TOPIC_AUDIO] += 1

    def on_all(_settings: Settings) -> None:
        notifications[TOPIC_ALL] += 1

    s.subscribe(TOPIC_AUDIO, on_audio)
    s.subscribe(TOPIC_ALL, on_all)

    audio = DummyAudio()

    # Initial apply
    s.apply_to_audio(audio)
    assert audio.master == pytest.approx(s.master_volume)
    assert audio.music == pytest.approx(s.effective_music_volume)
    assert audio.sfx == pytest.approx(s.effective_sfx_volume)

    # Update volumes and ensure observer + application correctness
    s.update(master_volume=0.6, music_volume=0.5, sfx_volume=0.4)

    assert notifications[TOPIC_AUDIO] == 1
    assert notifications[TOPIC_ALL] == 1

    # Apply again with updated settings
    s.apply_to_audio(audio)
    assert audio.master == pytest.approx(0.6)
    assert audio.music == pytest.approx(0.6 * 0.5)
    assert audio.sfx == pytest.approx(0.6 * 0.4)


def test_ui_observer_topic() -> None:
    s = Settings.from_sources()
    count = {"ui": 0}

    def on_ui(_s: Settings) -> None:
        count["ui"] += 1

    s.subscribe(TOPIC_UI, on_ui)
    s.update(show_minimap=False)
    s.update(fog_of_war=False)

    assert count["ui"] == 2


def test_invalid_update_field_raises() -> None:
    s = Settings.from_sources()
    with pytest.raises(AttributeError):
        s.update(nonexistent_field=True)  # type: ignore[arg-type]


def test_invalid_window_size_resets_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.clear()
    s = Settings.from_sources()
    with caplog.at_level("WARNING"):
        s.update(width=0, height=-5)
    assert s.width == 1280 and s.height == 720
    assert any("Invalid window size" in rec.message for rec in caplog.records)


def test_singleton_is_available() -> None:
    # The module-level SETTINGS should be a Settings instance and validated
    assert isinstance(SETTINGS, Settings)
    assert 0.0 <= SETTINGS.master_volume <= 1.0
