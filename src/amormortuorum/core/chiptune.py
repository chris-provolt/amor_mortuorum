"""A small 16-bit-console style synthesizer: four voices (pulse, triangle,
saw, noise) with envelopes and vibrato, rendering composed tracks and
designed sound effects to PCM with nothing but the standard library.

Everything is deterministic, so a cached render is identical every run.
Music tracks are written as chord progressions plus melody lines in a
compact text notation (``"E4:2 G4:2 -:4"`` = note name and length in
sixteenths; ``-`` is a rest); the bass and arpeggio parts are derived from
the chords so each track stays short to write. Tracks loop seamlessly: the
render is exactly the loop length and any note tail wraps round to the
start.

Effects are layered events (wave, pitch sweep, envelope, start offset) and
are tuned by ear-rules rather than sampled: a slash is a noise burst over a
falling pulse, fire is rumbling noise with a slow attack, frost a glassy
descending arpeggio, a bolt a screaming saw sweep.
"""
from __future__ import annotations

import array
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SAMPLE_RATE = 22050
PEAK = 32767

NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

_SINE = [math.sin(2 * math.pi * i / 1024) for i in range(1024)]


def note_hz(name: str) -> float:
    """Frequency of a note name such as ``A4``, ``C#3`` or ``Bb2`` (A4 = 440)."""
    letter = name[0].upper()
    rest = name[1:]
    semis = NOTE_INDEX[letter]
    while rest and rest[0] in "#b":
        semis += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    octave = int(rest)
    midi = 12 * (octave + 1) + semis
    return 440.0 * 2 ** ((midi - 69) / 12)


# --- Voices ------------------------------------------------------------------

class Voice:
    """How a part sounds: waveform, duty, envelope (seconds / level), vibrato."""

    def __init__(
        self, wave: str = "pulse", duty: float = 0.5, volume: float = 0.5,
        attack: float = 0.005, decay: float = 0.08, sustain: float = 0.7, release: float = 0.06,
        vibrato: float = 0.0, vibrato_rate: float = 5.5, gate: float = 0.9,
    ) -> None:
        self.wave = wave
        self.duty = duty
        self.volume = volume
        self.attack, self.decay, self.sustain, self.release = attack, decay, sustain, release
        self.vibrato, self.vibrato_rate = vibrato, vibrato_rate
        self.gate = gate  # share of the note length the key is held


def _render_tone(
    out: List[float], start: int, length: int, voice: Voice, f0: float, f1: Optional[float],
    held: Optional[int] = None, seed: int = 1, wrap: bool = False, amp: float = 1.0,
) -> None:
    """Add one note to ``out`` starting at sample ``start``: pitch glides from
    ``f0`` to ``f1`` over the note, the envelope releases after ``held`` samples
    (default the voice gate), and ``wrap`` folds samples past the end back to
    the beginning so loops stay seamless."""
    n = len(out)
    sr = SAMPLE_RATE
    held = int(length * voice.gate) if held is None else held
    a = max(1, int(voice.attack * sr))
    d = max(1, int(voice.decay * sr))
    r = max(1, int(voice.release * sr))
    total = held + r
    level = voice.volume * amp * PEAK * 0.5
    sustain = voice.sustain
    wave = voice.wave
    duty_cut = int(voice.duty * 65536)
    vib = voice.vibrato
    vib_rate = voice.vibrato_rate
    phase = 0
    state = (seed * 2654435761 + 12345) & 0x7FFFFFFF
    noise_v = 0.0
    noise_acc = 0.0
    f1 = f0 if f1 is None else f1
    for i in range(total):
        pos = start + i
        if pos >= n:
            if not wrap:
                break
            pos %= n
        # envelope
        if i < a:
            env = i / a
        elif i < a + d:
            env = 1.0 - (1.0 - sustain) * (i - a) / d
        elif i < held:
            env = sustain
        else:
            env = sustain * (1.0 - (i - held) / r)
            if env <= 0:
                break
        # pitch (glide + vibrato)
        t = i / sr
        freq = f0 + (f1 - f0) * min(1.0, i / max(1, length))
        if vib:
            freq *= 1.0 + vib * _SINE[int(t * vib_rate * 1024) & 1023]
        if wave == "noise":
            # pitched noise: a new random value every 1/freq seconds
            noise_acc += freq
            if noise_acc >= sr:
                noise_acc -= sr
                state = (state * 1103515245 + 12345) & 0x7FFFFFFF
                noise_v = state / 0x3FFFFFFF - 1.0
            v = noise_v
        else:
            phase = (phase + int(freq * 65536 / sr)) & 0xFFFF
            if wave == "pulse":
                v = 1.0 if phase < duty_cut else -1.0
            elif wave == "tri":
                v = 4.0 * abs(phase / 65536 - 0.5) - 1.0
            elif wave == "saw":
                v = phase / 32768 - 1.0
            else:  # sine
                v = _SINE[phase >> 6]
        out[pos] += v * env * level


def _finish(out: Sequence[float]) -> array.array:
    """Soft-clip and quantise to 16-bit PCM."""
    pcm = array.array("h", bytes(2 * len(out)))
    for i, v in enumerate(out):
        if v > PEAK * 0.8 or v < -PEAK * 0.8:
            v = math.copysign(PEAK * (0.8 + 0.2 * math.tanh((abs(v) / PEAK - 0.8) / 0.2)), v)
        pcm[i] = int(max(-PEAK, min(PEAK, v)))
    return pcm


# --- Music -------------------------------------------------------------------

LEAD = Voice("pulse", duty=0.25, volume=0.42, attack=0.004, decay=0.10, sustain=0.6,
             release=0.08, vibrato=0.006, vibrato_rate=5.0)
LEAD_SOFT = Voice("pulse", duty=0.125, volume=0.30, attack=0.01, decay=0.15, sustain=0.5,
                  release=0.12, vibrato=0.004, vibrato_rate=4.5)
HARMONY = Voice("pulse", duty=0.5, volume=0.22, attack=0.01, decay=0.2, sustain=0.5,
                release=0.1)
ARP = Voice("pulse", duty=0.125, volume=0.24, attack=0.002, decay=0.06, sustain=0.3,
            release=0.04, gate=0.6)
BASS = Voice("tri", volume=0.62, attack=0.004, decay=0.05, sustain=0.9, release=0.04, gate=0.85)
BASS_SAW = Voice("saw", volume=0.30, attack=0.004, decay=0.06, sustain=0.8, release=0.04,
                 gate=0.8)
PAD = Voice("sine", volume=0.30, attack=0.25, decay=0.3, sustain=0.8, release=0.4, gate=1.0,
            vibrato=0.003, vibrato_rate=3.0)
KICK = Voice("sine", volume=0.9, attack=0.001, decay=0.09, sustain=0.0, release=0.03)
SNARE = Voice("noise", volume=0.45, attack=0.001, decay=0.11, sustain=0.0, release=0.03)
HAT = Voice("noise", volume=0.16, attack=0.001, decay=0.025, sustain=0.0, release=0.01)
DRIP = Voice("sine", volume=0.35, attack=0.002, decay=0.12, sustain=0.0, release=0.05)

# chord name -> semitone offsets from the root
CHORDS = {"m": (0, 3, 7), "M": (0, 4, 7), "dim": (0, 3, 6), "m7": (0, 3, 7, 10),
          "sus2": (0, 2, 7), "M7": (0, 4, 7, 11)}


class Track:
    """A looping piece: tempo, bars of chords, and parts in text notation."""

    def __init__(
        self, bpm: int, chords: Sequence[str], *, melody: str = "", melody_voice: Voice = LEAD,
        harmony: Optional[str] = None, bass: str = "root", bass_voice: Voice = BASS,
        arp: Optional[str] = None, drums: Optional[str] = None, pad: bool = False,
        drips: int = 0, bass_octave: int = 2, arp_octave: int = 4, pad_octave: int = 3,
    ) -> None:
        self.bpm = bpm
        self.chords = list(chords)  # one per bar, e.g. "A3m", "F3M"
        self.melody = melody
        self.melody_voice = melody_voice
        self.harmony = harmony
        self.bass = bass          # "root" | "root5" | "walk" | "pulse8" | "riff:<notation>"
        self.bass_voice = bass_voice
        self.arp = arp            # "up8" | "updown16" | None
        self.drums = drums        # "rock" | "march" | "heavy" | None
        self.pad = pad
        self.drips = drips
        self.bass_octave = bass_octave
        self.arp_octave = arp_octave
        self.pad_octave = pad_octave

    @property
    def bars(self) -> int:
        return len(self.chords)

    @property
    def seconds(self) -> float:
        return self.bars * 4 * 60.0 / self.bpm


def parse_chord(token: str) -> Tuple[str, int, Tuple[int, ...]]:
    """``"A3m"`` -> ("A", 3, (0, 3, 7)); ``"Bb2M"`` -> ("Bb", 2, (0, 4, 7))."""
    i = 1
    while i < len(token) and token[i] in "#b":
        i += 1
    root = token[:i]
    j = i
    while j < len(token) and token[j].isdigit():
        j += 1
    octave = int(token[i:j])
    return root, octave, CHORDS[token[j:] or "M"]


def chord_notes(token: str, octave: Optional[int] = None) -> List[float]:
    root, oct_, offsets = parse_chord(token)
    base = note_hz(f"{root}{octave if octave is not None else oct_}")
    return [base * 2 ** (o / 12) for o in offsets]


def parse_notation(text: str) -> List[Tuple[Optional[str], int]]:
    """``"E4:2 G4:2 -:4"`` -> [("E4", 2), ("G4", 2), (None, 4)] (lengths in sixteenths)."""
    out: List[Tuple[Optional[str], int]] = []
    for tok in text.split():
        name, _, length = tok.partition(":")
        out.append((None if name == "-" else name, int(length or 1)))
    return out


def render_track(track: Track) -> array.array:
    """Render a looping track to 16-bit PCM (mono)."""
    sr = SAMPLE_RATE
    beat = 60.0 / track.bpm
    sixteenth = beat / 4
    n = int(round(track.bars * 4 * beat * sr))
    out = [0.0] * n
    six = int(sixteenth * sr)

    def place(voice: Voice, when: float, length_s: float, f0: float, f1: Optional[float] = None,
              seed: int = 1, amp: float = 1.0) -> None:
        _render_tone(out, int(when * sr), int(length_s * sr), voice, f0, f1,
                     seed=seed, wrap=True, amp=amp)

    def line(voice: Voice, notation: str, seed: int) -> None:
        t = 0.0
        for k, (name, length) in enumerate(parse_notation(notation)):
            dur = length * sixteenth
            if name is not None:
                place(voice, t, dur, note_hz(name), seed=seed + k)
            t += dur

    if track.melody:
        line(track.melody_voice, track.melody, 11)
    if track.harmony:
        line(HARMONY, track.harmony, 23)

    for bar, chord in enumerate(track.chords):
        t0 = bar * 4 * beat
        root, _, _ = parse_chord(chord)
        notes = chord_notes(chord, track.bass_octave)
        root_hz, fifth_hz = notes[0], notes[2]
        # bass
        if track.bass == "root":
            place(track.bass_voice, t0, 2 * beat, root_hz, seed=bar)
            place(track.bass_voice, t0 + 2 * beat, 2 * beat, root_hz, seed=bar + 1)
        elif track.bass == "root5":
            for b in range(4):
                place(track.bass_voice, t0 + b * beat, beat, root_hz if b % 2 == 0 else fifth_hz,
                      seed=bar * 4 + b)
        elif track.bass == "pulse8":
            for e in range(8):
                hz = root_hz if e not in (3, 7) else fifth_hz / 2
                place(track.bass_voice, t0 + e * beat / 2, beat / 2, hz, seed=bar * 8 + e)
        elif track.bass == "walk":
            steps = (root_hz, root_hz, notes[1], fifth_hz)
            for b in range(4):
                place(track.bass_voice, t0 + b * beat, beat, steps[b], seed=bar * 4 + b)
        elif track.bass.startswith("riff:"):
            pass  # rendered once below, not per bar
        # arpeggio
        if track.arp:
            arp_notes = chord_notes(chord, track.arp_octave)
            if track.arp == "up8":
                seq = [arp_notes[i % len(arp_notes)] for i in range(8)]
                step = beat / 2
            else:  # updown16
                cyc = arp_notes + arp_notes[-2:0:-1]
                seq = [cyc[i % len(cyc)] for i in range(16)]
                step = sixteenth
            for i, hz in enumerate(seq):
                place(ARP, t0 + i * step, step, hz, seed=100 + bar * 16 + i)
        # pad
        if track.pad:
            for i, hz in enumerate(chord_notes(chord, track.pad_octave)):
                place(PAD, t0, 4 * beat, hz, seed=200 + bar * 4 + i, amp=0.7)
        # drums
        if track.drums:
            kick_at = {"rock": (0, 8, 10), "march": (0, 4, 8, 12),
                       "heavy": (0, 6, 8, 14)}[track.drums]
            snare_at = {"rock": (4, 12), "march": (4, 12, 14), "heavy": (4, 12, 15)}[track.drums]
            for s in range(16):
                when = t0 + s * sixteenth
                if s in kick_at:
                    place(KICK, when, sixteenth, 150, 40, seed=300 + s)
                if s in snare_at:
                    place(SNARE, when, sixteenth, 1800, 600, seed=400 + s)
                if s % 2 == 0 or track.drums == "heavy":
                    place(HAT, when, sixteenth, 6000, seed=500 + s, amp=0.6 if s % 4 else 1.0)
        # drips: lonely echoing tones placed deterministically inside the bar
        for k in range(track.drips):
            h = (bar * 7919 + k * 104729) % 16
            hz = note_hz("E6") * 2 ** (((bar * 3 + k * 5) % 7) / 12)
            place(DRIP, t0 + h * sixteenth, sixteenth, hz, hz * 0.97, seed=600 + bar + k, amp=0.6)
            place(DRIP, t0 + (h + 3) * sixteenth, sixteenth, hz, hz * 0.97, seed=700 + bar + k,
                  amp=0.25)
    if track.bass.startswith("riff:"):
        line(track.bass_voice, track.bass[5:], 37)
    del six
    return _finish(out)


# --- The soundtrack ----------------------------------------------------------

MUSIC: Dict[str, Track] = {
    # Title: slow, mournful A minor; a lone lead over a soft pad and a walking bass.
    "title": Track(
        72, ["A2m", "F2M", "C3M", "E2M", "A2m", "F2M", "D2m", "E2M"],
        melody=(
            "E5:6 C5:2 D5:4 E5:4  F5:6 E5:2 D5:4 C5:4  E5:4 G5:4 E5:4 D5:4  B4:12 -:4  "
            "A4:6 C5:2 E5:4 D5:4  F5:6 A5:2 G5:4 F5:4  E5:4 D5:4 C5:4 B4:4  A4:12 -:4"
        ),
        melody_voice=LEAD_SOFT, bass="root", pad=True, pad_octave=3, bass_octave=2,
    ),
    # Graveyard: a music box in D minor, arpeggios turning under a sparse tune.
    "graveyard": Track(
        84, ["D3m", "Bb2M", "F3M", "A2M", "D3m", "Bb2M", "G2m", "A2M"],
        melody=(
            "-:8 A5:4 F5:4  -:8 D5:4 F5:4  -:8 A5:4 C6:4  A5:12 -:4  "
            "-:8 D6:4 C6:4  -:8 A5:4 F5:4  -:8 G5:4 A5:4  D5:12 -:4"
        ),
        melody_voice=LEAD_SOFT, bass="root", arp="updown16", arp_octave=4, bass_octave=2,
    ),
    # Dungeon: E minor, a low triangle ostinato, pulse stabs, water dripping.
    "dungeon": Track(
        92, ["E2m", "E2m", "C2M", "B2m", "E2m", "E2m", "A2m", "Bb2dim"],
        melody=(
            "-:12 B3:2 E4:2  -:16  -:12 G4:2 C4:2  -:16  "
            "-:12 B3:2 E4:2  -:16  -:8 A3:4 E4:4  Bb3:8 -:8"
        ),
        melody_voice=HARMONY, bass="pulse8", drips=1, bass_octave=2,
    ),
    # Deep floors: C# minor, saw bass grinding on half-steps, no comfort.
    "dungeon_deep": Track(
        100, ["C#2m", "D2M", "C#2m", "G2dim", "C#2m", "D2M", "A2m", "G#2M"],
        melody=(
            "-:8 C#4:4 D4:4  -:16  -:8 C#4:4 G4:4  -:16  "
            "-:8 E4:4 D4:4  -:16  -:8 A3:4 G#3:4  -:16"
        ),
        melody_voice=HARMONY, bass="root5", bass_voice=BASS_SAW, drips=2, pad=True,
        pad_octave=2, bass_octave=1,
    ),
    # Combat: driving D minor, drums and a riffing bass under a rhythmic lead.
    "combat": Track(
        150, ["D2m", "D2m", "F2M", "C2M", "D2m", "D2m", "Bb2M", "A2M"],
        melody=(
            "D5:2 D5:2 F5:2 D5:2 A5:4 G5:4  F5:2 E5:2 D5:2 C5:2 D5:8  "
            "F5:2 F5:2 A5:2 F5:2 C6:4 A5:4  C5:2 C5:2 E5:2 C5:2 G5:8  "
            "D5:2 D5:2 F5:2 D5:2 A5:4 G5:4  F5:2 E5:2 D5:2 C5:2 D5:8  "
            "Bb4:2 Bb4:2 D5:2 F5:2 D5:4 Bb4:4  A4:2 A4:2 C#5:2 E5:2 A5:8"
        ),
        bass="pulse8", drums="rock", bass_octave=2,
    ),
    # Boss: G minor, heavy drums, bass hammering the half-step above the root.
    "boss": Track(
        160, ["G2m", "G2m", "Eb2M", "D2M", "G2m", "G2m", "C#2dim", "D2M"],
        melody=(
            "G5:2 Ab5:2 G5:2 D5:2 G5:4 Bb5:4  A5:2 Bb5:2 A5:2 D5:2 G5:8  "
            "Eb5:2 Eb5:2 G5:2 Bb5:2 Eb6:4 D6:4  D5:2 D5:2 F#5:2 A5:2 D6:8  "
            "G5:2 Ab5:2 G5:2 D5:2 G5:4 Bb5:4  A5:2 Bb5:2 A5:2 D5:2 G5:8  "
            "C#5:2 G5:2 C#5:2 G5:2 Bb5:4 G5:4  D5:2 F#5:2 A5:2 D6:2 A5:8"
        ),
        bass="riff:" + "G2:2 G2:2 Ab2:2 G2:2 G2:2 G2:2 D2:2 G2:2 " * 2
             + "Eb2:2 Eb2:2 E2:2 Eb2:2 Eb2:2 Eb2:2 Bb1:2 Eb2:2 "
             + "D2:2 D2:2 Eb2:2 D2:2 D2:2 D2:2 A1:2 D2:2 "
             + "G2:2 G2:2 Ab2:2 G2:2 G2:2 G2:2 D2:2 G2:2 " * 2
             + "C#2:2 C#2:2 D2:2 C#2:2 C#2:2 C#2:2 G1:2 C#2:2 "
             + "D2:2 D2:2 Eb2:2 D2:2 D2:2 D2:2 A1:2 D2:2",
        bass_voice=BASS_SAW, drums="heavy", bass_octave=2,
    ),
}


def music_for_tier(tier: str) -> str:
    """Which dungeon track plays on a floor of the given tier."""
    return "dungeon_deep" if tier in ("T4", "T5") else "dungeon"


# --- Sound effects -----------------------------------------------------------

# Each effect is a list of layered events:
#   (voice, start_s, length_s, f0, f1 or None, amp)
Event = Tuple[Voice, float, float, float, Optional[float], float]

_BLIP = Voice("pulse", duty=0.5, volume=0.5, attack=0.002, decay=0.04, sustain=0.4, release=0.03)
_BLIP_SOFT = Voice("pulse", duty=0.25, volume=0.4, attack=0.002, decay=0.05, sustain=0.3,
                   release=0.04)
_NOISE = Voice("noise", volume=0.6, attack=0.002, decay=0.08, sustain=0.2, release=0.05)
_NOISE_SLOW = Voice("noise", volume=0.5, attack=0.08, decay=0.2, sustain=0.5, release=0.15)
_SWEEP = Voice("pulse", duty=0.5, volume=0.5, attack=0.002, decay=0.1, sustain=0.3, release=0.06)
_SAW = Voice("saw", volume=0.5, attack=0.002, decay=0.12, sustain=0.3, release=0.08)
_GLASS = Voice("sine", volume=0.5, attack=0.002, decay=0.15, sustain=0.2, release=0.1)
_CHIME = Voice("pulse", duty=0.125, volume=0.45, attack=0.002, decay=0.12, sustain=0.3,
               release=0.12, vibrato=0.005, vibrato_rate=6.0)
_BRASS = Voice("pulse", duty=0.5, volume=0.5, attack=0.03, decay=0.1, sustain=0.8, release=0.1,
               vibrato=0.01, vibrato_rate=5.0)
_ORGAN = Voice("tri", volume=0.6, attack=0.02, decay=0.1, sustain=0.8, release=0.15)
_THUD = Voice("sine", volume=0.9, attack=0.001, decay=0.12, sustain=0.0, release=0.05)
_SHIMMER = Voice("sine", volume=0.4, attack=0.05, decay=0.3, sustain=0.4, release=0.2,
                 vibrato=0.02, vibrato_rate=8.0)


def _arpeggio(voice: Voice, notes: Iterable[str], step: float, length: float, amp: float = 1.0,
              start: float = 0.0) -> List[Event]:
    return [(voice, start + i * step, length, note_hz(n), None, amp) for i, n in enumerate(notes)]


SFX: Dict[str, List[Event]] = {
    # UI
    "menu_move": [(_BLIP, 0.0, 0.04, 880, 1046, 0.6)],
    "menu_confirm": _arpeggio(_BLIP, ("C5", "G5"), 0.05, 0.07, 0.7),
    "menu_back": [(_BLIP, 0.0, 0.07, 660, 440, 0.6)],
    # Exploring
    "step": [(_NOISE, 0.0, 0.035, 900, 300, 0.45), (_THUD, 0.0, 0.03, 110, 60, 0.25)],
    "door": [(_NOISE_SLOW, 0.0, 0.3, 400, 120, 0.6), (_SAW, 0.02, 0.28, 90, 70, 0.3)],
    "chest": _arpeggio(_CHIME, ("E5", "G#5", "B5", "E6"), 0.06, 0.16, 0.8),
    "gold": _arpeggio(_BLIP, ("E6", "B6"), 0.05, 0.08, 0.6),
    "trap": [(_NOISE, 0.0, 0.05, 3000, 800, 0.8), (_SAW, 0.03, 0.22, 220, 90, 0.7)],
    "stairs": _arpeggio(_GLASS, ("E4", "C4", "A3", "F3"), 0.09, 0.2, 0.8),
    "portal": [(_SHIMMER, 0.0, 0.7, 440, 880, 0.8), (_SHIMMER, 0.1, 0.6, 659, 1319, 0.5)]
    + _arpeggio(_CHIME, ("A5", "C#6", "E6", "A6"), 0.08, 0.2, 0.5, start=0.15),
    "level_up": _arpeggio(_CHIME, ("G5", "B5", "D6", "G6"), 0.07, 0.18, 0.8)
    + [(_BRASS, 0.28, 0.35, note_hz("G5"), None, 0.5),
       (_BRASS, 0.28, 0.35, note_hz("B5"), None, 0.4)],
    "relic": [(_SHIMMER, 0.0, 0.9, 523, 1046, 0.7)]
    + _arpeggio(_GLASS, ("C6", "E6", "G6", "C7", "E7"), 0.09, 0.3, 0.6, start=0.05),
    "boss": [(_BRASS, 0.0, 0.5, note_hz("G2"), None, 0.9),
             (_BRASS, 0.0, 0.5, note_hz("C#3"), None, 0.6),
             (_THUD, 0.0, 0.3, 80, 30, 1.0), (_NOISE_SLOW, 0.1, 0.5, 300, 80, 0.5)],
    # Battle
    "slash": [(_NOISE, 0.0, 0.09, 4000, 1200, 0.7), (_SWEEP, 0.0, 0.1, 1200, 180, 0.5)],
    "hit": [(_NOISE, 0.0, 0.1, 1500, 300, 0.7), (_THUD, 0.0, 0.12, 140, 50, 0.9)],
    "cast": _arpeggio(_GLASS, ("C5", "E5", "G5"), 0.05, 0.12, 0.6),
    "spell": [(_SWEEP, 0.0, 0.25, 600, 1500, 0.5), (_NOISE, 0.1, 0.15, 2000, 800, 0.4)],
    "fire": [(_NOISE_SLOW, 0.0, 0.55, 500, 150, 0.9), (_NOISE, 0.05, 0.1, 3000, 2000, 0.3),
             (_NOISE, 0.2, 0.1, 2500, 1500, 0.3), (_THUD, 0.0, 0.3, 90, 40, 0.5)],
    "frost": _arpeggio(_GLASS, ("E7", "B6", "G6", "E6", "B5"), 0.05, 0.25, 0.6)
    + [(_NOISE, 0.0, 0.3, 7000, 3000, 0.25)],
    "wave": [(_BRASS, 0.0, 0.6, note_hz("D4"), note_hz("D4") * 1.01, 0.5),
             (_BRASS, 0.0, 0.6, note_hz("Ab4"), note_hz("Ab4") * 0.99, 0.4),
             (_SHIMMER, 0.1, 0.5, note_hz("D5"), note_hz("D6"), 0.4)],
    "bolt": [(_SAW, 0.0, 0.28, 2400, 90, 0.8), (_NOISE, 0.0, 0.08, 6000, 2000, 0.5),
             (_THUD, 0.18, 0.2, 120, 40, 0.8)],
    "heal": _arpeggio(_CHIME, ("C5", "E5", "G5", "C6"), 0.07, 0.2, 0.7)
    + [(_SHIMMER, 0.1, 0.4, 1046, 1568, 0.3)],
    "guard": [(_GLASS, 0.0, 0.3, 1200, 1150, 0.6), (_NOISE, 0.0, 0.04, 3000, 1000, 0.5),
              (_BLIP, 0.0, 0.08, 800, 600, 0.4)],
    "rage": [(_SAW, 0.0, 0.3, 80, 160, 0.7), (_NOISE_SLOW, 0.0, 0.3, 300, 500, 0.5)],
    "death": [(_SWEEP, 0.0, 0.4, 240, 40, 0.6), (_NOISE_SLOW, 0.0, 0.45, 800, 100, 0.6)],
    "flee": _arpeggio(_BLIP_SOFT, ("E5", "D5", "C5", "A4"), 0.045, 0.07, 0.6),
    "victory": _arpeggio(_BRASS, ("C5", "E5", "G5"), 0.1, 0.14, 0.7)
    + [(_BRASS, 0.3, 0.55, note_hz("C6"), None, 0.8), (_BRASS, 0.3, 0.55, note_hz("E5"), None, 0.5),
       (_BRASS, 0.3, 0.55, note_hz("G5"), None, 0.5),
       (_ORGAN, 0.3, 0.55, note_hz("C3"), None, 0.7)],
    "defeat": [(_ORGAN, 0.0, 0.3, note_hz("G3"), None, 0.7),
               (_ORGAN, 0.3, 0.3, note_hz("Eb3"), None, 0.7),
               (_ORGAN, 0.6, 0.7, note_hz("C3"), None, 0.8),
               (_ORGAN, 0.6, 0.7, note_hz("Gb3"), None, 0.5)],
}


def sfx_length(name: str) -> int:
    """Samples the rendered effect ``name`` occupies (events plus release tails)."""
    end = 0.0
    for voice, start, length, _, _, _ in SFX[name]:
        end = max(end, start + length * voice.gate + voice.release)
    return int(end * SAMPLE_RATE) + 1


def render_sfx(name: str) -> array.array:
    out = [0.0] * sfx_length(name)
    for k, (voice, start, length, f0, f1, amp) in enumerate(SFX[name]):
        _render_tone(out, int(start * SAMPLE_RATE), int(length * SAMPLE_RATE), voice, f0, f1,
                     seed=k + 1, amp=amp)
    return _finish(out)


__all__ = [
    "SAMPLE_RATE",
    "Voice",
    "Track",
    "MUSIC",
    "SFX",
    "note_hz",
    "parse_chord",
    "chord_notes",
    "parse_notation",
    "render_track",
    "render_sfx",
    "sfx_length",
    "music_for_tier",
]
