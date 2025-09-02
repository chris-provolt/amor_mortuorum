from __future__ import annotations

import math
from typing import Any, List, Optional

import pytest

from src.audio.ambient_manager import AmbientManager
from src.audio.interfaces import IAudioBackend
from src.config.audio_settings import AudioSettings
from src.core.scenes import SceneType


class FakePlayer:
    def __init__(self, path: str, loop: bool, volume: float) -> None:
        self.path = path
        self.loop = loop
        self.volume = volume
        self.stopped = False


class FakeAudioBackend(IAudioBackend):
    def __init__(self) -> None:
        self.started: List[FakePlayer] = []
        self.stopped: List[FakePlayer] = []

    def start_music(self, path: str, volume: float, loop: bool = True) -> FakePlayer:
        p = FakePlayer(path, loop, volume)
        self.started.append(p)
        return p

    def stop_music(self, player: FakePlayer) -> None:
        player.stopped = True
        self.stopped.append(player)

    def set_player_volume(self, player: FakePlayer, volume: float) -> None:
        player.volume = volume


@pytest.fixture
def track_map() -> dict:
    return {
        SceneType.HUB: "hub.ogg",
        SceneType.DUNGEON: "dungeon.ogg",
        SceneType.COMBAT: "combat.ogg",
    }


def test_scene_switch_plays_correct_track(track_map):
    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=1.0, music_volume=0.5)
    ambient = AmbientManager(backend, settings, track_map)

    ambient.on_scene_changed(SceneType.HUB)
    assert len(backend.started) == 1
    assert backend.started[-1].path == "hub.ogg"
    assert backend.started[-1].loop is True

    ambient.on_scene_changed(SceneType.DUNGEON)
    assert len(backend.started) == 2
    assert backend.started[-1].path == "dungeon.ogg"
    # Previous player stopped
    assert backend.stopped[0] is not None
    assert backend.stopped[0].stopped is True


def test_same_scene_no_restart(track_map):
    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=1.0, music_volume=1.0)
    ambient = AmbientManager(backend, settings, track_map)

    ambient.on_scene_changed(SceneType.HUB)
    ambient.on_scene_changed(SceneType.HUB)

    assert len(backend.started) == 1, "Should not restart the same scene's track"


def test_volume_respects_settings(track_map):
    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=0.5, music_volume=0.8)  # expected 0.4
    ambient = AmbientManager(backend, settings, track_map)

    ambient.on_scene_changed(SceneType.COMBAT)
    assert len(backend.started) == 1
    v = backend.started[0].volume
    assert math.isclose(v, 0.4, rel_tol=1e-6, abs_tol=1e-6)


def test_refresh_volume_after_settings_change(track_map):
    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=0.5, music_volume=0.8)  # 0.4
    ambient = AmbientManager(backend, settings, track_map)

    ambient.on_scene_changed(SceneType.HUB)
    assert math.isclose(backend.started[0].volume, 0.4, rel_tol=1e-6)

    # Update runtime settings and refresh volume
    settings.update(music_volume=0.25)  # 0.125 effective
    ambient.refresh_volume()
    assert math.isclose(backend.started[0].volume, 0.125, rel_tol=1e-6)


def test_missing_track_for_scene_stops(track_map):
    # Remove combat mapping
    del track_map[SceneType.COMBAT]

    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=1.0, music_volume=1.0)
    ambient = AmbientManager(backend, settings, track_map)

    ambient.on_scene_changed(SceneType.HUB)
    assert len(backend.started) == 1

    # Switch to combat which is unmapped -> should stop playback
    ambient.on_scene_changed(SceneType.COMBAT)
    assert len(backend.stopped) == 1
    # No new player should be started for COMBAT
    assert len(backend.started) == 1


def test_disable_then_enable_resumes_pending_scene(track_map):
    backend = FakeAudioBackend()
    settings = AudioSettings(master_volume=1.0, music_volume=1.0)
    ambient = AmbientManager(backend, settings, track_map)

    ambient.set_enabled(False)
    ambient.on_scene_changed(SceneType.DUNGEON)  # should be queued
    assert len(backend.started) == 0

    ambient.set_enabled(True)  # should resume queued scene
    assert len(backend.started) == 1
    assert backend.started[0].path == "dungeon.ogg"
