import math

from amormortuorum.systems.fov import Visibility, compute_fov, is_transparent
from amormortuorum.systems.procgen import FloorMap, Room, Tile, generate_floor


def _open_map(width=21, height=21):
    tiles = [[int(Tile.FLOOR)] * width for _ in range(height)]
    for x in range(width):
        tiles[0][x] = tiles[height - 1][x] = int(Tile.WALL)
    for y in range(height):
        tiles[y][0] = tiles[y][width - 1] = int(Tile.WALL)
    room = Room(1, 1, width - 2, height - 2)
    return FloorMap(1, 0, width, height, tiles, [room], (10, 10), (1, 1))


def test_origin_visible_and_radius_respected():
    m = _open_map()
    vis = compute_fov(m, (10, 10), radius=4)
    assert (10, 10) in vis
    assert (14, 10) in vis and (10, 14) in vis
    assert (15, 10) not in vis
    for x, y in vis:
        assert math.hypot(x - 10, y - 10) <= 4 + 1e-9


def test_open_room_is_fully_visible_within_radius():
    m = _open_map()
    vis = compute_fov(m, (10, 10), radius=30)
    for y in range(m.height):
        for x in range(m.width):
            assert (x, y) in vis, (x, y)  # walls at the edge are visible too


def test_wall_blocks_sight_but_is_itself_visible():
    m = _open_map()
    for y in range(1, 20):
        if y != 10:
            m.tiles[y][12] = int(Tile.WALL)  # a wall column with a single gap at y=10
    vis = compute_fov(m, (5, 10), radius=15)
    assert (12, 5) in vis  # the wall face is seen
    assert (16, 5) not in vis  # behind the wall
    assert (18, 10) in vis  # through the gap


def test_locked_door_blocks_and_open_door_does_not():
    m = _open_map()
    for y in range(1, 20):
        m.tiles[y][12] = int(Tile.WALL)
    m.tiles[10][12] = int(Tile.DOOR)
    m.doors[(12, 10)] = True
    assert not is_transparent(m, 12, 10)
    assert (16, 10) not in compute_fov(m, (5, 10), radius=15)
    m.unlock_door((12, 10))
    assert is_transparent(m, 12, 10)
    assert (16, 10) in compute_fov(m, (5, 10), radius=15)


def test_visibility_tracks_explored_and_changes():
    m = generate_floor(3, 2)
    vis = Visibility(radius=6)
    changed = vis.update(m, m.start)
    assert changed == vis.visible
    assert vis.state(m.start) == "visible"
    first = set(vis.visible)
    # Step to a neighbouring floor tile
    sx, sy = m.start
    neighbours = ((sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1))
    nxt = next(p for p in neighbours if m.is_walkable(*p))
    changed = vis.update(m, nxt)
    assert vis.explored >= first | vis.visible
    assert all(p in first or p in vis.visible for p in changed)
    remembered = vis.explored - vis.visible
    far = next(iter(remembered)) if remembered else None
    if far is not None:
        assert vis.state(far) == "explored"
    assert vis.state((0, 0)) in ("unknown", "visible", "explored")


def test_fov_on_generated_floor_stays_in_bounds_and_includes_room():
    m = generate_floor(7, 10)
    vis = compute_fov(m, m.start, radius=8)
    for x, y in vis:
        assert m.in_bounds(x, y)
    for cell in m.rooms[0].inner_cells():
        if math.hypot(cell[0] - m.start[0], cell[1] - m.start[1]) <= 8:
            assert cell in vis
