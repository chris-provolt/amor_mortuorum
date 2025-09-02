import pytest

from game.map.grid import MapGrid
from game.map.tiles import Tile
from game.movement.engine import Entity, MovementEngine, Position


def test_neighbors_edge_safety_no_diagonals():
    grid = MapGrid(2, 2, default_tile=Tile.FLOOR)

    # Top-left corner
    n00 = list(grid.neighbors(0, 0, diagonals=False))
    assert set(n00) == {(1, 0), (0, 1)}

    # Top-right corner
    n10 = list(grid.neighbors(1, 0, diagonals=False))
    assert set(n10) == {(0, 0), (1, 1)}

    # Bottom-left corner
    n01 = list(grid.neighbors(0, 1, diagonals=False))
    assert set(n01) == {(1, 1), (0, 0)}

    # Bottom-right corner
    n11 = list(grid.neighbors(1, 1, diagonals=False))
    assert set(n11) == {(0, 1), (1, 0)}


def test_neighbors_edge_safety_with_diagonals():
    grid = MapGrid(2, 2, default_tile=Tile.FLOOR)
    # Top-left corner should only return in-bounds diagonals
    n00d = set(grid.neighbors(0, 0, diagonals=True))
    assert n00d == {(1, 0), (0, 1), (1, 1)}


def test_movement_blocks_out_of_bounds_edges():
    grid = MapGrid(2, 2, default_tile=Tile.FLOOR)
    engine = MovementEngine()

    # Place entity at (0, 0)
    e = Entity(id="E1", pos=Position(0, 0))

    assert engine.try_move(e, -1, 0, grid) is False  # left out of bounds
    assert (e.pos.x, e.pos.y) == (0, 0)

    assert engine.try_move(e, 0, -1, grid) is False  # up out of bounds
    assert (e.pos.x, e.pos.y) == (0, 0)

    assert engine.try_move(e, -1, -1, grid) is False  # diagonal up-left OOB
    assert (e.pos.x, e.pos.y) == (0, 0)

    # Valid move to the right
    assert engine.try_move(e, 1, 0, grid) is True
    assert (e.pos.x, e.pos.y) == (1, 0)

    # From (1,0), moving right or up is OOB
    assert engine.try_move(e, 1, 0, grid) is False
    assert engine.try_move(e, 0, -1, grid) is False


def test_movement_blocks_at_bottom_right():
    grid = MapGrid(2, 2, default_tile=Tile.FLOOR)
    engine = MovementEngine()

    e = Entity(id="E2", pos=Position(1, 1))

    assert engine.try_move(e, 1, 0, grid) is False  # right OOB
    assert engine.try_move(e, 0, 1, grid) is False  # down OOB
    assert (e.pos.x, e.pos.y) == (1, 1)


def test_is_walkable_and_safe_get_never_raise():
    grid = MapGrid(3, 3, default_tile=Tile.FLOOR)
    # put walls around the border for additional safety
    for x in range(3):
        grid.set(x, 0, Tile.WALL)
        grid.set(x, 2, Tile.WALL)
    for y in range(3):
        grid.set(0, y, Tile.WALL)
        grid.set(2, y, Tile.WALL)

    # Out of bounds checks should be safe
    assert grid.is_walkable(-1, 1) is False
    assert grid.is_walkable(1, -1) is False
    assert grid.is_walkable(3, 1) is False
    assert grid.is_walkable(1, 3) is False

    assert grid.safe_get(-1, 1) is None
    assert grid.safe_get(1, -1) is None
    assert grid.safe_get(3, 1) is None
    assert grid.safe_get(1, 3) is None

    # get() should raise on OOB by design (to catch misuse), and our code avoids calling it unsafely
    with pytest.raises(IndexError):
        grid.get(-1, 0)


def test_one_by_one_map_bounds():
    grid = MapGrid(1, 1, default_tile=Tile.FLOOR)
    engine = MovementEngine()

    e = Entity(id="E3", pos=Position(0, 0))

    # All moves are OOB for 1x1 grid
    assert engine.try_move(e, -1, 0, grid) is False
    assert engine.try_move(e, 1, 0, grid) is False
    assert engine.try_move(e, 0, -1, grid) is False
    assert engine.try_move(e, 0, 1, grid) is False
    assert engine.try_move(e, -1, -1, grid) is False
    assert engine.try_move(e, 1, 1, grid) is False
    assert (e.pos.x, e.pos.y) == (0, 0)


def test_from_lines_and_to_lines_roundtrip():
    ascii_map = [
        "###",
        "#.#",
        "###",
    ]
    grid = MapGrid.from_lines(ascii_map)

    # Center is floor and walkable; edges are walls and not walkable
    assert grid.is_walkable(1, 1) is True
    assert grid.is_walkable(0, 0) is False

    # Bounds-safe neighbor generation at center should never include OOB
    neighbors = set(grid.neighbors(1, 1, diagonals=True))
    assert neighbors == {(0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (2, 0), (0, 2), (2, 2)}

    # Roundtrip ASCII conversion (void renders as space by default)
    assert grid.to_lines() == ascii_map
