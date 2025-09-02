from __future__ import annotations

import pytest

from amor.models.run_state import Character, Party, RunState


def test_party_and_character_validation() -> None:
    c = Character(name="Tara", level=2, hp=10, max_hp=12)
    p = Party(members=[c])
    rs = RunState(floor=1, dungeon_seed=1, party=p)
    rs.validate()  # should not raise

    with pytest.raises(ValueError):
        Character(name="", level=1, hp=1, max_hp=1).validate()

    with pytest.raises(ValueError):
        Character(name="Joe", level=0, hp=1, max_hp=1).validate()

    with pytest.raises(ValueError):
        Character(name="Joe", level=1, hp=2, max_hp=1).validate()

    with pytest.raises(ValueError):
        Party(members=[]).validate()

    with pytest.raises(ValueError):
        RunState(floor=0, dungeon_seed=1, party=p).validate()
