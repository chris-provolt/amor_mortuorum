import math
import random

import pytest

from amor.map.grid import MapGrid
from amor.fov.fog_of_war import FogOfWar, FogSettings, FogTileState
from amor.fov.fov import compute_fov


def test_fov_open_room_visibility():
    # 7x7 open grid
    grid = MapGrid(7, 7, default_transparent=True)
    fow = FogOfWar(grid, FogSettings(vision_radius=3, dim_factor=0.35))

    # Center player
    player = (3, 3)
    fow.update(player)
    light = fow.light_map()

    # All tiles within Chebyshev distance <= 3 are visible (brightness 1.0)
    for y in range(grid.height):
        for x in range(grid.width):
            dist = max(abs(x - player[0]), abs(y - player[1]))
            if dist <= 3:
                assert light[y][x] == pytest.approx(1.0)
            else:
                assert light[y][x] == pytest.approx(0.0)


def test_fov_wall_blocks_sight_and_wall_is_visible():
    # 7x5 grid with a vertical wall at x=3
    rows = [
        "..#....",
        "..#....",
        "..#....",
        "..#....",
        "..#....",
    ]
    grid = MapGrid.from_ascii(rows, wall_chars=("#",))

    fow = FogOfWar(grid, FogSettings(vision_radius=10))
    player = (1, 2)  # left side of the wall
    fow.update(player)

    # The wall tile in direct line should be visible
    assert fow.get_state(2, 2) == FogTileState.VISIBLE

    # Tiles behind the wall on same row should be unseen (blocked)
    assert fow.get_state(4, 2) == FogTileState.UNSEEN
    assert fow.get_state(6, 2) == FogTileState.UNSEEN


def test_memory_seen_dim_when_not_visible():
    # Open grid 7x7
    grid = MapGrid(7, 7, default_transparent=True)
    settings = FogSettings(vision_radius=2, dim_factor=0.4)
    fow = FogOfWar(grid, settings)

    # Step 1: player at center sees a radius-2 diamond (Chebyshev)
    p1 = (3, 3)
    fow.update(p1)
    light1 = fow.light_map()

    # A tile at distance 2 is visible
    assert light1[3][5] == pytest.approx(1.0)

    # Step 2: move player far away so the tile is out of range
    p2 = (0, 0)
    fow.update(p2)
    light2 = fow.light_map()

    # The previously visible tile should now be dim, not dark
    assert light2[3][5] == pytest.approx(settings.dim_factor)

    # And a tile never seen far away should still be dark
    assert light2[6][6] == pytest.approx(0.0)


def test_reset_memory():
    grid = MapGrid(5, 5, default_transparent=True)
    fow = FogOfWar(grid, FogSettings(vision_radius=3))

    fow.update((2, 2))
    assert fow.get_state(2, 2) == FogTileState.VISIBLE
    assert fow.get_state(0, 0) != FogTileState.UNSEEN  # seen/dim or visible depending on radius

    fow.reset_memory()
    # After reset, only current visibility counts
    # Without update, querying current state for non-visible should be UNSEEN
    assert fow.get_state(0, 0) == FogTileState.UNSEEN


def test_fov_function_with_opaque_targets():
    rows = [
        "........",
        "........",
        "....#...",
        "........",
        "........",
    ]
    grid = MapGrid.from_ascii(rows)
    origin = (1, 2)
    visible = compute_fov(grid, origin, 10, include_opaque_targets=True)

    # Wall tile should be visible as a target, but tiles behind it not
    assert (4, 2) in visible  # wall
    assert (5, 2) not in visible


def test_on_map_changed_resets_memory():
    grid1 = MapGrid(4, 4, default_transparent=True)
    fow = FogOfWar(grid1, FogSettings(vision_radius=1))
    fow.update((1, 1))
    assert fow.get_state(1, 1) == FogTileState.VISIBLE

    grid2 = MapGrid(6, 3, default_transparent=False)
    fow.on_map_changed(grid2)

    # New grid, all unseen and not visible
    with pytest.raises(IndexError):
        _ = fow.get_state(5, 4)

    assert fow.get_state(0, 0) == FogTileState.UNSEEN


def test_dim_factor_bounds():
    with pytest.raises(ValueError):
        _ = FogSettings(vision_radius=3, dim_factor=-0.1)
    with pytest.raises(ValueError):
        _ = FogSettings(vision_radius=3, dim_factor=1.1)


def test_invalid_parameters():
    grid = MapGrid(3, 3)
    fow = FogOfWar(grid)
    with pytest.raises(ValueError):
        fow.update((-1, 0))
    with pytest.raises(ValueError):
        fow.update((0, 0), radius=-1)

    with pytest.raises(ValueError):
        _ = MapGrid(0, 3)
    with pytest.raises(ValueError):
        _ = MapGrid(3, 0)

    # from_ascii shape check
    with pytest.raises(ValueError):
        _ = MapGrid.from_ascii(["..", "."])
