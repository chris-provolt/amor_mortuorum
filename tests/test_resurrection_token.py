import logging

import pytest

from amormortuorum.config import GRAVEYARD_LOCATION_NAME, RESURRECTION_POLICY, ResurrectionPolicy
from amormortuorum.core.events import EventBus
from amormortuorum.game.game_state import GameState
from amormortuorum.items.resurrection_token import create_resurrection_token
from amormortuorum.models.inventory import Inventory
from amormortuorum.models.player import Player


@pytest.fixture(autouse=True)
def _configure_logging():
    logging.basicConfig(level=logging.DEBUG)
    yield


def make_player_with_tokens(name: str, max_hp: int, hp: int, num_tokens: int) -> Player:
    inv = Inventory()
    for _ in range(num_tokens):
        inv.add(create_resurrection_token())
    return Player(name=name, max_hp=max_hp, hp=hp, inventory=inv)


def test_death_with_resurrection_token_revives_and_consumes_token(monkeypatch):
    # Ensure deterministic HP policy for test
    monkeypatch.setattr(
        "amormortuorum.config.RESURRECTION_POLICY",
        ResurrectionPolicy(hp_policy="one"),
        raising=False,
    )

    events = EventBus()
    revived_event = {"count": 0}

    def on_revived(event_name, payload):
        revived_event["count"] += 1
        assert event_name == "player_revived"
        assert payload["consumed_item_id"] == "resurrection_token"

    events.on("player_revived", on_revived)

    gs = GameState(current_location="Dungeon", events=events)
    player = make_player_with_tokens("Hero", max_hp=20, hp=5, num_tokens=1)

    # Lethal damage triggers death handler
    player.take_damage(999, gs)

    # Acceptance criteria: revived at Graveyard with token consumed
    assert player.is_alive() is True
    assert player.hp == 1  # per test policy override
    assert gs.current_location == GRAVEYARD_LOCATION_NAME
    assert player.inventory.count_by_id("resurrection_token") == 0
    assert revived_event["count"] == 1


def test_death_without_token_results_in_permadeath_and_no_location_change():
    events = EventBus()
    gs = GameState(current_location="Dungeon", events=events)
    player = make_player_with_tokens("Hero", max_hp=20, hp=10, num_tokens=0)

    player.take_damage(15, gs)

    assert player.is_alive() is False
    assert player.hp == 0
    assert gs.current_location == "Dungeon"  # unchanged


def test_multiple_tokens_only_one_consumed_on_revive(monkeypatch):
    # Use half policy to ensure HP computed as expected
    monkeypatch.setattr(
        "amormortuorum.config.RESURRECTION_POLICY",
        ResurrectionPolicy(hp_policy="half"),
        raising=False,
    )

    events = EventBus()
    gs = GameState(current_location="Depth-33", events=events)
    player = make_player_with_tokens("Hero", max_hp=21, hp=21, num_tokens=3)

    # First lethal
    player.take_damage(1000, gs)
    assert player.is_alive() is True
    # ceil(21/2) = 11
    assert player.hp == 11
    assert gs.current_location == GRAVEYARD_LOCATION_NAME
    assert player.inventory.count_by_id("resurrection_token") == 2

    # Second lethal (simulate going back to dungeon then dying again)
    gs.current_location = "Depth-34"
    player.take_damage(1000, gs)
    assert player.is_alive() is True
    assert player.hp == 11
    assert gs.current_location == GRAVEYARD_LOCATION_NAME
    assert player.inventory.count_by_id("resurrection_token") == 1


if __name__ == "__main__":
    pytest.main([__file__])
