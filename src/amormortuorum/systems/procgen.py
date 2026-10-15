"""Procedural floor generation: BSP rooms joined by L-shaped corridors.

Pure Python; every random decision comes from ``floor_rng(seed, floor)`` so a
floor is a deterministic function of ``(seed, floor)``.

Coordinates are tile (x, y) with the origin at the bottom-left and y growing
upward, matching Arcade's world space. ``FloorMap.tiles`` is indexed
``tiles[y][x]``.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from random import Random
from typing import List, Optional, Set, Tuple

from .rng import floor_rng

TILE_SIZE = 32

PORTAL_BASE_CHANCE = 0.30
PORTAL_DECAY = 0.985
PORTAL_MIN_CHANCE = 0.02

Pos = Tuple[int, int]


class Tile(IntEnum):
    WALL = 0
    FLOOR = 1


def portal_chance(floor: int) -> float:
    """Chance that a portal back to the Graveyard spawns on ``floor`` (rarer deeper)."""
    return max(PORTAL_MIN_CHANCE, PORTAL_BASE_CHANCE * PORTAL_DECAY ** (floor - 1))


def chest_count_for_floor(floor: int, rng: Random) -> int:
    """Number of chests on a floor: 1-3 on the first tier, up to 2-5 deeper down."""
    bonus = min(2, (floor - 1) // 20)  # 0 on floors 1-20, 1 on 21-40, 2 from 41
    return rng.randint(1 + bonus, 3 + bonus)


@dataclass(frozen=True)
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Pos:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def inner_cells(self) -> List[Pos]:
        return [
            (cx, cy)
            for cy in range(self.y, self.y + self.h)
            for cx in range(self.x, self.x + self.w)
        ]

    def contains(self, pos: Pos) -> bool:
        x, y = pos
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def intersects(self, other: "Room", margin: int = 1) -> bool:
        return (
            self.x - margin < other.x + other.w
            and other.x - margin < self.x + self.w
            and self.y - margin < other.y + other.h
            and other.y - margin < self.y + self.h
        )


@dataclass
class FloorMap:
    floor: int
    seed: int
    width: int
    height: int
    tiles: List[List[int]]
    rooms: List[Room]
    start: Pos
    stairs: Pos
    chests: Set[Pos] = field(default_factory=set)
    portal: Optional[Pos] = None

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            return Tile.WALL
        return self.tiles[y][x]

    def is_walkable(self, x: int, y: int) -> bool:
        return self.tile(x, y) == Tile.FLOOR

    def feature_at(self, x: int, y: int) -> Optional[str]:
        pos = (x, y)
        if pos == self.stairs:
            return "stairs"
        if pos in self.chests:
            return "chest"
        if self.portal is not None and pos == self.portal:
            return "portal"
        return None

    def remove_chest(self, pos: Pos) -> bool:
        """Remove an opened chest; return whether one was there."""
        if pos in self.chests:
            self.chests.discard(pos)
            return True
        return False


def bfs_reachable(fmap: FloorMap, start: Pos) -> Set[Pos]:
    """All floor tiles reachable from ``start`` by 4-neighbour movement."""
    if not fmap.is_walkable(*start):
        return set()
    seen: Set[Pos] = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in seen and fmap.is_walkable(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


# ---------------------------------------------------------------------------
# BSP generation


@dataclass
class _Leaf:
    x: int
    y: int
    w: int
    h: int
    left: Optional["_Leaf"] = None
    right: Optional["_Leaf"] = None
    room: Optional[Room] = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def _split(leaf: _Leaf, rng: Random, min_leaf: int, depth: int, max_depth: int) -> None:
    if depth >= max_depth:
        return
    can_h = leaf.h >= 2 * min_leaf
    can_v = leaf.w >= 2 * min_leaf
    if not can_h and not can_v:
        return
    if can_h and can_v:
        # Prefer splitting along the longer axis to keep leaves roughly square.
        if leaf.w > leaf.h * 1.25:
            horizontal = False
        elif leaf.h > leaf.w * 1.25:
            horizontal = True
        else:
            horizontal = rng.random() < 0.5
    else:
        horizontal = can_h
    if horizontal:
        cut = rng.randint(min_leaf, leaf.h - min_leaf)
        leaf.left = _Leaf(leaf.x, leaf.y, leaf.w, cut)
        leaf.right = _Leaf(leaf.x, leaf.y + cut, leaf.w, leaf.h - cut)
    else:
        cut = rng.randint(min_leaf, leaf.w - min_leaf)
        leaf.left = _Leaf(leaf.x, leaf.y, cut, leaf.h)
        leaf.right = _Leaf(leaf.x + cut, leaf.y, leaf.w - cut, leaf.h)
    _split(leaf.left, rng, min_leaf, depth + 1, max_depth)
    _split(leaf.right, rng, min_leaf, depth + 1, max_depth)


def _make_room(leaf: _Leaf, rng: Random, min_room: int, max_room: int) -> Room:
    # Keep a 1-tile wall margin inside the leaf so neighbouring rooms never touch.
    avail_w = leaf.w - 2
    avail_h = leaf.h - 2
    w = rng.randint(min(min_room, avail_w), min(max_room, avail_w))
    h = rng.randint(min(min_room, avail_h), min(max_room, avail_h))
    x = rng.randint(leaf.x + 1, leaf.x + leaf.w - 1 - w)
    y = rng.randint(leaf.y + 1, leaf.y + leaf.h - 1 - h)
    return Room(x, y, w, h)


def _carve_room(tiles: List[List[int]], room: Room) -> None:
    for cx, cy in room.inner_cells():
        tiles[cy][cx] = Tile.FLOOR


def _carve_h(tiles: List[List[int]], x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        tiles[y][x] = Tile.FLOOR


def _carve_v(tiles: List[List[int]], y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        tiles[y][x] = Tile.FLOOR


def _carve_corridor(tiles: List[List[int]], a: Pos, b: Pos, rng: Random) -> None:
    """L-shaped corridor between two points; the bend direction is random."""
    (x1, y1), (x2, y2) = a, b
    if rng.random() < 0.5:
        _carve_h(tiles, x1, x2, y1)
        _carve_v(tiles, y1, y2, x2)
    else:
        _carve_v(tiles, y1, y2, x1)
        _carve_h(tiles, x1, x2, y2)


def _any_room(leaf: _Leaf, rng: Random) -> Room:
    """A room somewhere inside this subtree (used as a corridor endpoint)."""
    if leaf.room is not None:
        return leaf.room
    children = [c for c in (leaf.left, leaf.right) if c is not None]
    return _any_room(rng.choice(children), rng)


def _connect(leaf: _Leaf, tiles: List[List[int]], rng: Random) -> None:
    if leaf.is_leaf:
        return
    assert leaf.left is not None and leaf.right is not None
    _connect(leaf.left, tiles, rng)
    _connect(leaf.right, tiles, rng)
    a = _any_room(leaf.left, rng)
    b = _any_room(leaf.right, rng)
    _carve_corridor(tiles, a.center, b.center, rng)


def _collect_rooms(leaf: _Leaf, out: List[Room]) -> None:
    if leaf.is_leaf:
        if leaf.room is not None:
            out.append(leaf.room)
        return
    assert leaf.left is not None and leaf.right is not None
    _collect_rooms(leaf.left, out)
    _collect_rooms(leaf.right, out)


def _manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def generate_floor(
    seed: int,
    floor: int,
    width: int = 48,
    height: int = 32,
    *,
    min_room: int = 4,
    max_room: int = 9,
    max_depth: int = 5,
) -> FloorMap:
    """Generate a deterministic floor layout for ``(seed, floor)``."""
    if width < 8 or height < 8:
        raise ValueError("Floor grid must be at least 8x8")
    rng = floor_rng(seed, floor)
    tiles: List[List[int]] = [[int(Tile.WALL)] * width for _ in range(height)]

    # Leave a 1-tile border of wall around the whole grid.
    root = _Leaf(1, 1, width - 2, height - 2)
    min_leaf = min_room + 2  # room + its 1-tile inner margin
    _split(root, rng, min_leaf, 0, max_depth)

    def place_rooms(leaf: _Leaf) -> None:
        if leaf.is_leaf:
            leaf.room = _make_room(leaf, rng, min_room, max_room)
            _carve_room(tiles, leaf.room)
            return
        assert leaf.left is not None and leaf.right is not None
        place_rooms(leaf.left)
        place_rooms(leaf.right)

    place_rooms(root)
    _connect(root, tiles, rng)

    rooms: List[Room] = []
    _collect_rooms(root, rooms)

    if len(rooms) < 2:
        # Tiny grid: carve a second room in the opposite corner and join them.
        first = rooms[0]
        w = min(min_room, width - 4)
        h = min(min_room, height - 4)
        if first.center[0] < width // 2:
            x = width - 1 - w - 1
        else:
            x = 2
        if first.center[1] < height // 2:
            y = height - 1 - h - 1
        else:
            y = 2
        second = Room(x, y, w, h)
        _carve_room(tiles, second)
        _carve_corridor(tiles, first.center, second.center, rng)
        rooms.append(second)

    start_room = rooms[0]
    start = start_room.center
    stairs_room = max(rooms[1:], key=lambda r: (_manhattan(r.center, start), -rooms.index(r)))
    stairs = stairs_room.center

    # Chests: random interior floor cells excluding start/stairs.
    reserved = {start, stairs}
    candidates = [c for r in rooms for c in r.inner_cells() if c not in reserved]
    chests: Set[Pos] = set()
    want = chest_count_for_floor(floor, rng)
    for _ in range(want):
        if not candidates:
            break
        pos = rng.choice(candidates)
        candidates.remove(pos)
        chests.add(pos)

    # Portal: depth-decaying chance, never in the start room (nor stairs room if possible).
    portal: Optional[Pos] = None
    if rng.random() < portal_chance(floor):
        eligible = [r for r in rooms if r is not start_room]
        if len(rooms) > 2:
            eligible = [r for r in eligible if r is not stairs_room]
        if eligible:
            room = rng.choice(eligible)
            cells = [c for c in room.inner_cells() if c not in reserved and c not in chests]
            if cells:
                portal = rng.choice(cells)

    return FloorMap(
        floor=floor,
        seed=seed,
        width=width,
        height=height,
        tiles=tiles,
        rooms=rooms,
        start=start,
        stairs=stairs,
        chests=chests,
        portal=portal,
    )


__all__ = [
    "TILE_SIZE",
    "PORTAL_BASE_CHANCE",
    "PORTAL_DECAY",
    "PORTAL_MIN_CHANCE",
    "Pos",
    "Tile",
    "Room",
    "FloorMap",
    "portal_chance",
    "chest_count_for_floor",
    "generate_floor",
    "bfs_reachable",
]
