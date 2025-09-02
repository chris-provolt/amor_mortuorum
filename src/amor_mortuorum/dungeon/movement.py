from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .map import DungeonMap, Point


@dataclass
class MoveResult:
    new_pos: Point
    moved: bool


def try_move(dmap: DungeonMap, pos: Point, dx: int, dy: int) -> MoveResult:
    """
    Attempt to move from pos by (dx, dy). Never performs out-of-bounds tile
    access; treats out-of-bounds as non-walkable. Returns MoveResult with new
    position if moved.
    """
    target_x = pos.x + dx
    target_y = pos.y + dy
    if not dmap.in_bounds(target_x, target_y):
        return MoveResult(new_pos=pos, moved=False)
    if not dmap.is_walkable(target_x, target_y):
        return MoveResult(new_pos=pos, moved=False)
    return MoveResult(new_pos=Point(target_x, target_y), moved=True)
