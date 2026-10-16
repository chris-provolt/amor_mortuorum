from random import Random

import pytest

from amormortuorum.data import GameData
from amormortuorum.systems.monsters import (
    FLEE_COOLDOWN,
    MONSTER_MEMORY,
    SPAWN_MIN_DIST,
    Monster,
    daze,
    distance_field,
    maybe_respawn,
    monster_at,
    monster_count,
    monster_rng,
    remove_monster,
    spawn_monsters,
    step_monsters,
)
from amormortuorum.systems.procgen import FloorMap, Tile, bfs_reachable, generate_floor


@pytest.fixture(scope="module")
def data() -> GameData:
    return GameData.load()


def corridor(length: int = 12) -> FloorMap:
    """A straight 1-tile corridor along y=1, from x=1 to x=length."""
    width, height = length + 2, 3
    tiles = [[Tile.WALL] * width for _ in range(height)]
    for x in range(1, length + 1):
        tiles[1][x] = Tile.FLOOR
    return FloorMap(
        floor=1, seed=0, width=width, height=height, tiles=tiles, rooms=[],
        start=(1, 1), stairs=(length, 1),
    )


def test_spawn_is_deterministic_and_off_the_start(data):
    for floor in (1, 7, 30, 99):
        fmap = generate_floor(11, floor)
        a = spawn_monsters(fmap, floor, data, monster_rng(11, floor))
        b = spawn_monsters(fmap, floor, data, monster_rng(11, floor))
        assert [(m.pos, m.enemies) for m in a] == [(m.pos, m.enemies) for m in b]
        assert a, "every floor starts with at least one roaming group"
        reachable = bfs_reachable(fmap, fmap.start)
        near = distance_field(fmap, fmap.start, SPAWN_MIN_DIST - 1)
        positions = [m.pos for m in a]
        assert len(set(positions)) == len(positions)
        for m in a:
            assert m.pos in reachable and m.pos not in near
            assert m.pos not in fmap.chests and m.pos != fmap.stairs
            assert all(data.enemy(eid) for eid in m.enemies)
            assert m.spd >= 1 and m.name


def test_monster_count_grows_with_depth(data):
    rng = Random(0)
    shallow = sum(monster_count(1, data.balance, rng) for _ in range(500)) / 500
    deep = sum(monster_count(99, data.balance, rng) for _ in range(500)) / 500
    assert deep > shallow
    assert all(monster_count(1, data.balance, Random(s)) >= 1 for s in range(50))


def test_distance_field_counts_steps_and_respects_limit():
    fmap = corridor(10)
    field = distance_field(fmap, (1, 1), 4)
    assert field[(1, 1)] == 0 and field[(5, 1)] == 4
    assert (6, 1) not in field and (1, 0) not in field
    blocked = distance_field(fmap, (1, 1), 10, blocked={(3, 1)})
    assert (4, 1) not in blocked


def test_visible_monster_chases_and_catches():
    fmap = corridor(12)
    m = Monster(id=0, pos=(6, 1), enemies=("skel_basic",), name="Skeleton", spd=5)
    monsters = [m]
    visible = set(fmap.tiles and ((x, 1) for x in range(1, 13)))
    rng = Random(1)
    caught = step_monsters(monsters, fmap, (1, 1), visible, rng, step=1, player_spd=5)
    assert caught is None and m.chasing and m.pos == (5, 1)
    for step in range(2, 10):
        caught = step_monsters(monsters, fmap, (1, 1), visible, rng, step=step, player_spd=5)
        if caught is not None:
            break
    assert caught is m and m.pos == (1, 1)


def test_slow_monster_moves_every_other_step_while_chasing():
    fmap = corridor(12)
    m = Monster(id=0, pos=(8, 1), enemies=("skel_basic",), name="Skeleton", spd=2)
    visible = {(x, 1) for x in range(1, 13)}
    rng = Random(3)
    moved = []
    for step in range(0, 6):
        before = m.pos
        step_monsters([m], fmap, (1, 1), visible, rng, step=step, player_spd=9)
        moved.append(m.pos != before)
    assert moved == [True, False, True, False, True, False]


def test_chaser_forgets_after_memory_runs_out():
    fmap = corridor(12)
    m = Monster(id=0, pos=(10, 1), enemies=("skel_basic",), name="Skeleton", spd=9,
                state="chase", memory=MONSTER_MEMORY)
    rng = Random(0)
    # Player out of sight: memory ticks down and the state flips to wander at zero.
    for _ in range(MONSTER_MEMORY - 1):
        step_monsters([m], fmap, (1, 1), set(), rng, step=0, player_spd=1)
        assert m.chasing
    step_monsters([m], fmap, (1, 1), set(), rng, step=0, player_spd=1)
    assert not m.chasing


def test_wanderers_stay_on_floor_and_never_overlap(data):
    fmap = generate_floor(5, 3)
    rng = monster_rng(5, 3)
    monsters = spawn_monsters(fmap, 3, data, rng)
    player = fmap.start
    for step in range(300):
        step_monsters(monsters, fmap, player, set(), rng, step=step, player_spd=5)
        positions = [m.pos for m in monsters]
        assert len(set(positions)) == len(positions)
        for m in monsters:
            assert fmap.is_walkable(*m.pos)
            assert m.pos != player and m.pos != fmap.stairs


def test_daze_flee_cooldown_and_removal():
    fmap = corridor(12)
    m = Monster(id=0, pos=(3, 1), enemies=("skel_basic",), name="Skeleton", spd=9,
                state="chase", memory=MONSTER_MEMORY)
    daze(m)
    assert not m.chasing and m.cooldown == FLEE_COOLDOWN
    visible = {(x, 1) for x in range(1, 13)}
    rng = Random(0)
    for _ in range(FLEE_COOLDOWN):
        assert step_monsters([m], fmap, (2, 1), visible, rng) is None
        assert m.pos == (3, 1)
    step_monsters([m], fmap, (2, 1), visible, rng)
    assert m.chasing  # awake again and adjacent: next step catches
    monsters = [m]
    assert monster_at(monsters, m.pos) is m and monster_at(monsters, (9, 9)) is None
    remove_monster(monsters, m)
    assert monsters == []


def test_respawn_only_below_strength_and_out_of_sight(data):
    fmap = generate_floor(9, 10)
    rng = Random(2)
    full = spawn_monsters(fmap, 10, data, Random(0))
    target = int(round(data.balance.monsters_base + data.balance.monsters_per_floor * 9))
    full = full[:target] if len(full) >= target else full + full[: target - len(full)]
    assert maybe_respawn(full, fmap, 10, fmap.start, data, rng) is None
    monsters = []
    spawned = None
    visible = set(distance_field(fmap, fmap.start, 8))
    for _ in range(2000):
        spawned = maybe_respawn(monsters, fmap, 10, fmap.start, data, rng, visible=visible)
        if spawned is not None:
            break
    assert spawned is not None and spawned.pos not in visible
    assert spawned.pos in bfs_reachable(fmap, fmap.start)
