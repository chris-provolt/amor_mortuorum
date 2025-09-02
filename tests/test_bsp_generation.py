import itertools

from amor_mortuorum.dungeon.bsp import BSPDungeonGenerator
from amor_mortuorum.dungeon.map import TileType
from amor_mortuorum.dungeon.movement import try_move


def test_deterministic_layout():
    gen = BSPDungeonGenerator(seed_base=12345)
    d1, s1, st1 = gen.generate(floor=7, width=60, height=38)
    d2, s2, st2 = gen.generate(floor=7, width=60, height=38)

    assert d1.snapshot() == d2.snapshot(), "Tiles differ with same seed+floor"
    assert s1 == s2, "Start differs with same seed+floor"
    assert st1 == st2, "Stairs differ with same seed+floor"


def test_reachability_start_to_stairs():
    gen = BSPDungeonGenerator(seed_base=987654321)
    dmap, start, stairs = gen.generate(floor=1, width=64, height=40)

    # BFS from start must reach stairs
    dist = dmap.bfs_distance_map(start)
    assert dist[stairs.y][stairs.x] is not None, "Stairs must be reachable from start"


def test_no_out_of_bounds_movement():
    gen = BSPDungeonGenerator(seed_base=42)
    dmap, start, _stairs = gen.generate(floor=3, width=32, height=24)

    # Probe corners and attempt to step outside repeatedly
    corners = [(0, 0), (dmap.width - 1, 0), (0, dmap.height - 1), (dmap.width - 1, dmap.height - 1)]
    deltas = [(-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (1, 1)]

    for cx, cy in corners:
        from amor_mortuorum.dungeon.map import Point
        pos = Point(cx, cy)
        for dx, dy in deltas:
            result = try_move(dmap, pos, dx, dy)
            assert not result.moved
            assert result.new_pos == pos


def test_map_has_walls_border():
    gen = BSPDungeonGenerator(seed_base=2024)
    dmap, _start, _stairs = gen.generate(floor=5, width=50, height=30)

    # Ensure the outer border is all walls - prevents OOB pathing issues
    for x in range(dmap.width):
        assert dmap.get_tile(x, 0) == TileType.WALL
        assert dmap.get_tile(x, dmap.height - 1) == TileType.WALL
    for y in range(dmap.height):
        assert dmap.get_tile(0, y) == TileType.WALL
        assert dmap.get_tile(dmap.width - 1, y) == TileType.WALL


def test_nonzero_rooms_and_corridors():
    gen = BSPDungeonGenerator(seed_base="run-abc")
    dmap, _start, _stairs = gen.generate(floor=2, width=48, height=32)

    floors = 0
    for y in range(dmap.height):
        for x in range(dmap.width):
            t = dmap.get_tile(x, y)
            if t != TileType.WALL:
                floors += 1
    assert floors > (dmap.width * dmap.height) * 0.15, "Expect at least 15% non-wall tiles"
