from amor_mortuorum.engine.game_state import GameState
from amor_mortuorum.engine.events import GameEvent


def test_descend_stairs_advances_floor_and_resets_spawn():
    width, height = 10, 10
    state = GameState(seed=42, map_width=width, map_height=height)

    # Stairs are at (width-2, height-2); spawn at (1,1)
    stairs_target = (width - 2, height - 2)

    # Collect events
    events = []
    state.add_listener(lambda e, s: events.append(e))

    # Move to the stairs tile step by step
    # Move horizontally to x = width - 2
    while state.player_pos[0] < stairs_target[0]:
        assert state.move(1, 0) is True
    # Move vertically to y = height - 2
    while state.player_pos[1] < stairs_target[1]:
        assert state.move(0, 1) is True

    # The last move should have triggered a descent
    assert state.floor == 2
    # Player should be reset to new floor's spawn (1,1)
    assert state.player_pos == (1, 1)

    # FLOOR_CHANGED event should be in events
    assert GameEvent.FLOOR_CHANGED in events

    # Ensure moves still work on new floor (sanity)
    assert state.move(1, 0) is True
    assert state.player_pos == (2, 1)
