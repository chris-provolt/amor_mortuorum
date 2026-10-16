import wave
from pathlib import Path

from amormortuorum.core import chiptune
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


def test_rendered_effects_are_valid_wavs(tmp_path):
    for name in PLACEHOLDER_SFX:
        path = synthesize_sfx(name, tmp_path / f"{name}.wav")
        with wave.open(str(path)) as wf:
            assert wf.getnchannels() == 1 and wf.getsampwidth() == 2
            assert wf.getframerate() == SAMPLE_RATE
            assert wf.getnframes() == chiptune.sfx_length(name)
            assert 0.02 < wf.getnframes() / SAMPLE_RATE < 2.0, name


def test_music_tracks_loop_to_the_bar(tmp_path):
    name = "combat"
    track = PLACEHOLDER_MUSIC[name]
    path = synthesize_music(name, tmp_path / f"{name}.wav")
    with wave.open(str(path)) as wf:
        assert wf.getnframes() == int(round(track.seconds * SAMPLE_RATE))
        assert 10 < track.seconds < 90
    expected = {"title", "graveyard", "dungeon", "dungeon_deep", "combat", "boss"}
    assert set(PLACEHOLDER_MUSIC) >= expected
    assert chiptune.music_for_tier("T1") == "dungeon"
    assert chiptune.music_for_tier("T5") == "dungeon_deep"


def test_every_cue_the_scenes_play_exists():
    import re
    from pathlib import Path as P

    src = P(__file__).resolve().parents[1] / "src" / "amormortuorum" / "scenes"
    text = "\n".join(p.read_text(encoding="utf-8") for p in src.glob("*.py"))
    for cue in set(re.findall(r'audio\.play\("([a-z_]+)"', text)):
        assert cue in PLACEHOLDER_SFX, cue
    for cue in set(re.findall(r'play_music\("([a-z_]+)"', text)):
        assert cue in PLACEHOLDER_MUSIC, cue
    for cue in ("slash", "fire", "frost", "bolt", "wave", "cast", "guard", "death", "rage"):
        assert cue in PLACEHOLDER_SFX


def test_synth_notation_and_levels():
    assert abs(chiptune.note_hz("A4") - 440) < 1e-6
    assert abs(chiptune.note_hz("A5") - 880) < 1e-6
    assert abs(chiptune.note_hz("Bb3") - chiptune.note_hz("A#3")) < 1e-6
    assert chiptune.parse_notation("E4:2 -:4 G#4") == [("E4", 2), (None, 4), ("G#4", 1)]
    assert chiptune.parse_chord("Bb2M") == ("Bb", 2, (0, 4, 7))
    pcm = chiptune.render_sfx("slash")
    peak = max(abs(v) for v in pcm)
    assert 3000 < peak <= chiptune.PEAK
    # rendering is deterministic
    assert chiptune.render_sfx("heal").tobytes() == chiptune.render_sfx("heal").tobytes()


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
    assert (tmp_path / "v2" / "sfx" / "chest.wav").exists()
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
