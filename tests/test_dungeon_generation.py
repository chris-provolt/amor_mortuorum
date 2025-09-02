import os

from amor.config import GenerationSettings
from amor.dungeon.factory import DungeonFactory
from amor.dungeon.pathfinding import find_path_bfs
from amor.dungeon.tiles import Tile


def assert_navigable(grid):
    # Entrance and exit must be floors
    ex, ey = grid.entrance
    tx, ty = grid.exit
    assert grid.is_floor(ex, ey)
    assert grid.is_floor(tx, ty)

    # Path between entrance and exit
    dist = find_path_bfs(grid, grid.entrance, grid.exit)
    assert dist is not None and dist > 0

    # No out-of-bounds floors and borders are walls
    for x in range(grid.width):
        assert grid.tiles[0][x] == Tile.WALL
        assert grid.tiles[grid.height - 1][x] == Tile.WALL
    for y in range(grid.height):
        assert grid.tiles[y][0] == Tile.WALL
        assert grid.tiles[y][grid.width - 1] == Tile.WALL

    # There should be a reasonable amount of floor
    floors = sum(1 for y in range(grid.height) for x in range(grid.width) if grid.tiles[y][x] == Tile.FLOOR)
    frac = floors / float(grid.width * grid.height)
    assert 0.15 <= frac <= 0.8


def test_bsp_rooms_navigable():
    settings = GenerationSettings(algorithm="bsp", width=60, height=40, seed=123, max_rooms=15)
    grid = DungeonFactory.generate(settings)
    assert_navigable(grid)


def test_cellular_cavern_navigable():
    settings = GenerationSettings(
        algorithm="cellular",
        width=60,
        height=40,
        seed=123,
        cell_initial_wall_prob=0.45,
        cell_smooth_steps=5,
        cell_wall_threshold=5,
        cell_min_floor_fraction=0.25,
    )
    grid = DungeonFactory.generate(settings)
    assert_navigable(grid)


def test_env_switch_algorithm(monkeypatch):
    # Verify environment-based selection works and doesn't crash
    monkeypatch.setenv("AMOR_DUNGEON_ALGO", "cellular")
    monkeypatch.setenv("AMOR_WIDTH", "50")
    monkeypatch.setenv("AMOR_HEIGHT", "35")
    monkeypatch.setenv("AMOR_SEED", "42")
    settings = GenerationSettings.from_env()
    grid = DungeonFactory.generate(settings)
    assert_navigable(grid)

    # Switch back to bsp
    monkeypatch.setenv("AMOR_DUNGEON_ALGO", "bsp")
    settings = GenerationSettings.from_env()
    grid = DungeonFactory.generate(settings)
    assert_navigable(grid)
