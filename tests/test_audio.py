import wave
from pathlib import Path

from amormortuorum.core.audio import (
    PLACEHOLDER_MUSIC,
    PLACEHOLDER_SFX,
    SAMPLE_RATE,
    AudioManager,
    NullAudio,
    synthesize_music,
    synthesize_sfx,
)
from amormortuorum.core.settings import Settings


class FakePlayer:
    def __init__(self):
        self.paused = False
        self.deleted = False
        self.volume = None

    def pause(self):
        self.paused = True

    def delete(self):
        self.deleted = True


class FakeSound:
    def __init__(self, path: Path):
        self.path = path
        self.plays = []

    def play(self, volume=1.0, loop=False, **_):
        self.plays.append((volume, loop))
        player = FakePlayer()
        player.volume = volume
        return player


def test_placeholder_tones_are_valid_wavs(tmp_path):
    for name in PLACEHOLDER_SFX:
        path = synthesize_sfx(name, tmp_path / f"{name}.wav")
        with wave.open(str(path)) as wf:
            assert wf.getnchannels() == 1 and wf.getsampwidth() == 2
            assert wf.getframerate() == SAMPLE_RATE
            expected = sum(int(SAMPLE_RATE * sec) for _, sec, _ in PLACEHOLDER_SFX[name])
            assert wf.getnframes() == expected
    for name, (_, seconds) in PLACEHOLDER_MUSIC.items():
        path = synthesize_music(name, tmp_path / f"{name}.wav")
        with wave.open(str(path)) as wf:
            assert wf.getnframes() == int(SAMPLE_RATE * seconds)


def test_manager_plays_sfx_at_setting_volume_and_caches(tmp_path):
    settings = Settings.load()
    settings.audio.sfx_volume = 0.4
    made = {}

    def loader(path):
        made[path.name] = FakeSound(path)
        return made[path.name]

    audio = AudioManager(settings, tmp_path, loader=loader, enabled=True)
    assert audio.play("chest") is True
    assert audio.play("chest") is True
    assert made["chest.wav"].plays == [(0.4, False), (0.4, False)]
    assert (tmp_path / "sfx" / "chest.wav").exists()
    assert audio.play("not_a_sound") is False

    settings.audio.sfx_volume = 0.0
    assert audio.play("chest") is False  # muted


def test_music_loops_switches_and_stops(tmp_path):
    settings = Settings.load()
    settings.audio.music_volume = 0.25
    made = {}

    def loader(path):
        made[path.name] = FakeSound(path)
        return made[path.name]

    audio = AudioManager(settings, tmp_path, loader=loader, enabled=True)
    audio.play_music("graveyard")
    assert audio.current_music == "graveyard"
    assert made["graveyard.wav"].plays == [(0.25, True)]
    first = audio._music_player

    audio.play_music("graveyard")  # same track: no restart
    assert made["graveyard.wav"].plays == [(0.25, True)]

    settings.audio.music_volume = 0.9
    audio.apply_volumes()
    assert first.volume == 0.9

    audio.play_music("dungeon")
    assert first.paused and first.deleted
    assert audio.current_music == "dungeon"
    audio.play_music(None)
    assert audio.current_music is None and audio._music_player is None


def test_disabled_manager_and_null_audio_are_silent(tmp_path):
    audio = AudioManager(Settings.load(), tmp_path, loader=lambda p: FakeSound(p), enabled=False)
    assert audio.play("hit") is False
    audio.play_music("dungeon")
    assert audio.current_music is None
    null = NullAudio()
    assert null.play("hit") is False
    null.play_music("x")
    null.stop_music()
