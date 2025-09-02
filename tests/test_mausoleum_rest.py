import logging

import pytest

from amor_mortuorum.core.party import Character, Party
from amor_mortuorum.hub.mausoleum import rest_at_mausoleum, CONFIRMATION_TEXT, REST_SOUND_CUE
from amor_mortuorum.core.audio import AudioManager


class FakeAudioManager(AudioManager):
    def __init__(self, available: bool) -> None:
        self.available = available
        self.played: list[str] = []

    def has_cue(self, cue: str) -> bool:
        return self.available

    def play(self, cue: str) -> None:
        # Simulate playing by recording the cue name
        self.played.append(cue)


def test_rest_full_heal_and_revive_all_members():
    party = Party(
        members=[
            Character(name="Aerin", max_hp=50, max_mp=10, hp=12, mp=2),
            Character(name="Brom", max_hp=80, max_mp=0, hp=0, mp=0),  # downed
        ]
    )

    result = rest_at_mausoleum(party)

    assert result.message == CONFIRMATION_TEXT
    assert result.healed_members == 2
    assert result.revived_members == 1

    # All members should be fully restored
    for m in party.members:
        assert m.hp == m.max_hp
        assert m.mp == m.max_mp


def test_rest_plays_sound_if_available():
    audio = FakeAudioManager(available=True)

    party = Party(
        members=[
            Character(name="Ciri", max_hp=30, max_mp=5, hp=10, mp=1),
        ]
    )

    result = rest_at_mausoleum(party, audio=audio)

    assert result.sound_played is True
    assert audio.played == [REST_SOUND_CUE]


def test_rest_skips_sound_if_unavailable():
    audio = FakeAudioManager(available=False)

    party = Party(
        members=[
            Character(name="Dorian", max_hp=40, max_mp=6, hp=35, mp=3),
        ]
    )

    result = rest_at_mausoleum(party, audio=audio)

    assert result.sound_played is False
    assert audio.played == []


def test_rest_without_revive_option_does_not_revive():
    party = Party(
        members=[
            Character(name="Eira", max_hp=45, max_mp=12, hp=0, mp=0),  # downed
            Character(name="Fen", max_hp=25, max_mp=3, hp=10, mp=0),
        ]
    )

    result = rest_at_mausoleum(party, revive_downed=False)

    # In this mode, the downed member remains at 0 HP but MP is maxed by heal_full()
    assert result.healed_members == 2  # Both got resources set to max values
    assert result.revived_members == 0

    assert party.members[0].hp == party.members[0].max_hp  # heal_full sets to full even if downed
    assert party.members[1].hp == party.members[1].max_hp


def test_invalid_party_raises():
    with pytest.raises(ValueError):
        rest_at_mausoleum(None)  # type: ignore[arg-type]
