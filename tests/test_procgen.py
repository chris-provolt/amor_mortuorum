import pytest

from amormortuorum.systems.procgen import (
    DOOR_MIN_FLOOR,
    PORTAL_MIN_CHANCE,
    TRAP_KINDS,
    FloorMap,
    Room,
    Tile,
    bfs_reachable,
    generate_floor,
    portal_chance,
    trap_damage,
)

PAIRS = [
    (1, 1), (2, 1), (3, 7), (42, 20), (7, 33),
    (99, 50), (5, 61), (1234, 80), (8, 99), (9001, 99),
]


def _snapshot(m: FloorMap):
    return (
        m.tiles, m.rooms, m.start, m.stairs, sorted(m.chests), m.portal,
        sorted((p, t.kind) for p, t in m.traps.items()), sorted(m.doors), sorted(m.keys),
    )


@pytest.mark.parametrize("seed", [1, 42, 9001])
def test_generation_is_deterministic(seed):
    a = generate_floor(seed, 3)
    b = generate_floor(seed, 3)
    assert _snapshot(a) == _snapshot(b)


def test_different_seeds_differ():
    assert _snapshot(generate_floor(1, 1)) != _snapshot(generate_floor(2, 1))


def test_different_floors_differ():
    assert _snapshot(generate_floor(1, 1)) != _snapshot(generate_floor(1, 2))


@pytest.mark.parametrize("seed,floor", PAIRS)
def test_start_and_stairs_walkable_distinct_connected(seed, floor):
    m = generate_floor(seed, floor)
    assert m.is_walkable(*m.start)
    assert m.is_walkable(*m.stairs)
    assert m.start != m.stairs
    reachable = bfs_reachable(m, m.start, through_locked_doors=True)
    assert m.stairs in reachable
    # Every room is reachable, so the whole floor is connected.
    for room in m.rooms:
        assert room.center in reachable


@pytest.mark.parametrize("seed,floor", PAIRS)
def test_features_on_floor_tiles(seed, floor):
    m = generate_floor(seed, floor)
    assert 1 <= len(m.chests) <= 5
    for pos in m.chests:
        assert m.is_walkable(*pos)
        assert pos not in (m.start, m.stairs)
    if m.portal is not None:
        assert m.is_walkable(*m.portal)
        assert m.portal not in (m.start, m.stairs)
        assert m.portal not in m.chests
        assert not m.rooms[0].contains(m.portal)


@pytest.mark.parametrize("seed,floor", PAIRS)
def test_border_is_wall(seed, floor):
    m = generate_floor(seed, floor)
    for x in range(m.width):
        assert m.tiles[0][x] == Tile.WALL
        assert m.tiles[m.height - 1][x] == Tile.WALL
    for y in range(m.height):
        assert m.tiles[y][0] == Tile.WALL
        assert m.tiles[y][m.width - 1] == Tile.WALL
    assert not m.is_walkable(-1, 0)
    assert not m.is_walkable(m.width, m.height)


def test_portal_chance_formula():
    assert portal_chance(1) == 0.30
    assert portal_chance(50) == pytest.approx(0.30 * 0.985 ** 49)
    assert portal_chance(99) == pytest.approx(max(0.02, 0.30 * 0.985 ** 98))
    assert portal_chance(10_000) == PORTAL_MIN_CHANCE


def test_portal_frequency_on_floor_one_matches_chance():
    with_portal = sum(1 for seed in range(1, 201) if generate_floor(seed, 1).portal is not None)
    assert 0.18 <= with_portal / 200 <= 0.42


def test_feature_at_and_remove_chest():
    m = generate_floor(3, 1)
    assert m.feature_at(*m.stairs) == "stairs"
    chest = next(iter(m.chests))
    assert m.feature_at(*chest) == "chest"
    assert m.remove_chest(chest) is True
    assert m.feature_at(*chest) is None
    assert m.remove_chest(chest) is False
    if m.portal is not None:
        assert m.feature_at(*m.portal) == "portal"
    assert m.feature_at(0, 0) is None


def test_small_grid_still_has_two_connected_rooms():
    m = generate_floor(5, 1, width=12, height=10, max_depth=0)
    assert len(m.rooms) >= 2
    assert m.start != m.stairs
    assert m.stairs in bfs_reachable(m, m.start)


def test_room_helpers():
    a = Room(2, 2, 4, 3)
    b = Room(7, 2, 3, 3)
    assert a.center == (4, 3)
    assert len(a.inner_cells()) == 12
    assert a.contains((5, 4)) and not a.contains((6, 2))
    assert not a.intersects(b, margin=0)
    assert a.intersects(b, margin=2)


@pytest.mark.parametrize("seed,floor", PAIRS)
def test_traps_are_hidden_one_shot_hazards_off_features(seed, floor):
    m = generate_floor(seed, floor)
    for pos, trap in m.traps.items():
        assert m.tile(*pos) == Tile.FLOOR
        assert pos not in m.chests and pos != m.start and pos != m.stairs and pos != m.portal
        assert pos not in m.keys and pos not in m.doors
        assert trap.kind in TRAP_KINDS and trap.armed and not trap.revealed
        assert m.feature_at(*pos) is None  # hidden until triggered
    if m.traps:
        pos, trap = next(iter(m.traps.items()))
        assert m.trigger_trap(pos) is trap
        assert trap.revealed and not trap.armed
        assert m.feature_at(*pos) == "trap"
        assert m.trigger_trap(pos) is None


def test_trap_damage_scales_with_depth():
    assert trap_damage("spikes", 1) == 4
    assert trap_damage("darts", 1) == 2
    assert trap_damage("spikes", 60) > trap_damage("spikes", 1)
    assert trap_damage("spikes", 30) > trap_damage("darts", 30)


def test_floor_one_never_locks_the_stairs():
    for seed in range(1, 60):
        assert not generate_floor(seed, 1).doors


def test_locked_stairs_rooms_have_a_reachable_key():
    locked = [generate_floor(seed, 5) for seed in range(1, 121)]
    locked = [m for m in locked if m.doors]
    assert len(locked) >= 15, "about a third of floors should lock the stairs room"
    for m in locked:
        assert 5 >= DOOR_MIN_FLOOR
        assert all(m.tile(*pos) == Tile.DOOR and locked_ for pos, locked_ in m.doors.items())
        assert len(m.keys) == 1
        key = next(iter(m.keys))
        without = bfs_reachable(m, m.start)
        assert key in without, "key must be reachable without passing a door"
        assert m.stairs not in without, "stairs must be sealed behind the doors"
        assert m.feature_at(*key) == "key"
        door = next(iter(m.doors))
        assert m.feature_at(*door) == "door"
        assert not m.is_walkable(*door)
        # Unlocking every door opens the way to the stairs
        for pos in list(m.doors):
            assert m.unlock_door(pos) is True
            assert m.unlock_door(pos) is False
        assert m.is_walkable(*door)
        assert m.stairs in bfs_reachable(m, m.start)
        assert m.pickup_key(key) is True and m.pickup_key(key) is False
