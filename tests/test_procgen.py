import pytest

from amormortuorum.systems.procgen import (
    PORTAL_MIN_CHANCE,
    FloorMap,
    Room,
    Tile,
    bfs_reachable,
    generate_floor,
    portal_chance,
)

PAIRS = [
    (1, 1), (2, 1), (3, 7), (42, 20), (7, 33),
    (99, 50), (5, 61), (1234, 80), (8, 99), (9001, 99),
]


def _snapshot(m: FloorMap):
    return (m.tiles, m.rooms, m.start, m.stairs, sorted(m.chests), m.portal)


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
    reachable = bfs_reachable(m, m.start)
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
