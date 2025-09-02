import pytest

from amor_mortuorum.engine.game_state import GameState
from amor_mortuorum.engine.events import GameEvent


def test_blocked_by_walls_and_floor_walkable():
    state = GameState(seed=123, map_width=10, map_height=10)

    # Initial spawn is (1,1) in generator
    assert state.player_pos == (1, 1)

    # Attempt to move into wall to the left (x=0) -> blocked
    moved = state.move(-1, 0)
    assert moved is False
    assert state.player_pos == (1, 1)

    # Move right onto floor -> allowed
    moved = state.move(1, 0)
    assert moved is True
    assert state.player_pos == (2, 1)

    # Move up into wall boundary -> should be blocked when reaching y=1 to y=0
    # Move back to (1,1) first
    assert state.move(-1, 0) is True
    assert state.player_pos == (1, 1)

    # Try to move up into wall (y=0)
    assert state.move(0, -1) is False
    assert state.player_pos == (1, 1)


def test_only_cardinal_movement():
    state = GameState(seed=123, map_width=10, map_height=10)
    # Diagonal should be rejected
    assert state.move(1, 1) is False
    assert state.player_pos == (1, 1)


def test_player_moved_event_emitted():
    state = GameState(seed=123, map_width=10, map_height=10)
    events = []
    state.add_listener(lambda e, s: events.append(e))

    # Move right -> should emit PLAYER_MOVED
    assert state.move(1, 0) is True
    assert GameEvent.PLAYER_MOVED in events
