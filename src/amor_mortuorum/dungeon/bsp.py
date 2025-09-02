from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .map import DungeonMap, Point, Rect, TileType

logger = logging.getLogger(__name__)


@dataclass
class Leaf:
    rect: Rect
    left: Optional['Leaf'] = None
    right: Optional['Leaf'] = None
    room: Optional[Rect] = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class BSPDungeonGenerator:
    """
    BSP (Binary Space Partition) room + corridor generator.

    Guarantees:
    - Deterministic layout given (seed_base, floor)
    - Start and stairs are placed on connected floor tiles
    - One-tile wall border to prevent OOB access by movement
    """

    def __init__(self, seed_base: int | str) -> None:
        self.seed_base = seed_base

    @staticmethod
    def _combine_seed(seed_base: int | str, floor: int) -> int:
        if isinstance(seed_base, int):
            return ((seed_base & 0xFFFFFFFF) << 16) ^ (floor & 0xFFFF)
        # String or others: use stable hash via md5
        h = hashlib.md5(f"{seed_base}:{floor}".encode("utf-8")).hexdigest()
        return int(h[:16], 16)  # use 64-bit worth

    def generate(
        self,
        floor: int,
        width: int = 64,
        height: int = 40,
        min_leaf_size: int = 8,
        max_leaf_size: int = 20,
        room_min_size: int = 4,
        room_max_size: Optional[int] = None,
    ) -> Tuple[DungeonMap, Point, Point]:
        """
        Generate a dungeon map using BSP.

        Returns: (map, start, stairs_down)
        """
        if room_max_size is None:
            room_max_size = max(6, min_leaf_size - 2)
        if room_min_size >= room_max_size:
            room_max_size = room_min_size + 1

        rng_seed = self._combine_seed(self.seed_base, floor)
        rng = random.Random(rng_seed)
        logger.debug("Generating BSP dungeon: seed=%s floor=%d size=%dx%d", str(self.seed_base), floor, width, height)

        # Prepare map; margins of 1 wall around edges
        dmap = DungeonMap(width, height, default=TileType.WALL)

        # Root leaf excludes the outer wall border to make corridors easier
        root = Leaf(Rect(1, 1, width - 2, height - 2))
        leaves: List[Leaf] = [root]

        # Split leaves
        did_split = True
        while did_split:
            did_split = False
            new_leaves: List[Leaf] = []
            for leaf in leaves:
                if leaf.is_leaf():
                    if leaf.rect.w > max_leaf_size or leaf.rect.h > max_leaf_size or rng.random() > 0.8:
                        if self._split_leaf(leaf, rng, min_leaf_size):
                            new_leaves.append(leaf.left)  # type: ignore[arg-type]
                            new_leaves.append(leaf.right)  # type: ignore[arg-type]
                            did_split = True
                if not leaf.is_leaf():
                    # Already split; keep it to connect later
                    new_leaves.append(leaf)
            if did_split:
                leaves = new_leaves

        # Create rooms in leaves
        rooms: List[Rect] = []
        self._create_rooms(root, rng, rooms, room_min_size, room_max_size)

        # Carve rooms
        for room in rooms:
            dmap.carve_room(room)

        # Connect rooms via leaf tree
        self._connect_children(root, rng, dmap)

        # Choose start and stairs
        # Start: pick random room's center
        if not rooms:
            raise RuntimeError("BSP generation failed: no rooms created")
        start_room = rng.choice(rooms)
        start = start_room.center()
        # Ensure start is a floor tile
        dmap.set_tile(start.x, start.y, TileType.FLOOR)

        # Farthest reachable from start
        far = dmap.farthest_reachable(start)
        if far is None:
            # Extreme fallback: place stairs in start room center
            far = start
        dmap.set_tile(far.x, far.y, TileType.STAIRS_DOWN)

        dmap.start = start
        dmap.stairs_down = far

        return dmap, start, far

    def _split_leaf(self, leaf: Leaf, rng: random.Random, min_leaf_size: int) -> bool:
        if not leaf.is_leaf():
            return False
        split_horiz = rng.choice([True, False])
        if leaf.rect.w / leaf.rect.h >= 1.25:
            split_horiz = False
        elif leaf.rect.h / leaf.rect.w >= 1.25:
            split_horiz = True

        max_split = (leaf.rect.h if split_horiz else leaf.rect.w) - min_leaf_size
        if max_split <= min_leaf_size:
            return False

        split = rng.randint(min_leaf_size, max_split)
        if split_horiz:
            left_rect = Rect(leaf.rect.x, leaf.rect.y, leaf.rect.w, split)
            right_rect = Rect(leaf.rect.x, leaf.rect.y + split, leaf.rect.w, leaf.rect.h - split)
        else:
            left_rect = Rect(leaf.rect.x, leaf.rect.y, split, leaf.rect.h)
            right_rect = Rect(leaf.rect.x + split, leaf.rect.y, leaf.rect.w - split, leaf.rect.h)

        leaf.left = Leaf(left_rect)
        leaf.right = Leaf(right_rect)
        return True

    def _create_rooms(
        self,
        leaf: Leaf,
        rng: random.Random,
        out_rooms: List[Rect],
        room_min_size: int,
        room_max_size: int,
    ) -> None:
        if leaf.is_leaf():
            w = rng.randint(room_min_size, max(room_min_size, min(room_max_size, leaf.rect.w - 1)))
            h = rng.randint(room_min_size, max(room_min_size, min(room_max_size, leaf.rect.h - 1)))
            x = rng.randint(leaf.rect.x, leaf.rect.x + leaf.rect.w - w)
            y = rng.randint(leaf.rect.y, leaf.rect.y + leaf.rect.h - h)
            leaf.room = Rect(x, y, w, h)
            out_rooms.append(leaf.room)
        else:
            if leaf.left:
                self._create_rooms(leaf.left, rng, out_rooms, room_min_size, room_max_size)
            if leaf.right:
                self._create_rooms(leaf.right, rng, out_rooms, room_min_size, room_max_size)

    def _connect_children(self, leaf: Leaf, rng: random.Random, dmap: DungeonMap) -> None:
        if leaf.left and leaf.right:
            self._connect_children(leaf.left, rng, dmap)
            self._connect_children(leaf.right, rng, dmap)
            # Connect rooms from this leaf's children
            left_room = self._get_room_in_leaf(leaf.left, rng)
            right_room = self._get_room_in_leaf(leaf.right, rng)
            if left_room and right_room:
                self._connect_rooms(left_room, right_room, rng, dmap)

    def _get_room_in_leaf(self, leaf: Leaf, rng: random.Random) -> Optional[Rect]:
        if leaf.is_leaf():
            return leaf.room
        rooms: List[Rect] = []
        if leaf.left:
            r = self._get_room_in_leaf(leaf.left, rng)
            if r:
                rooms.append(r)
        if leaf.right:
            r = self._get_room_in_leaf(leaf.right, rng)
            if r:
                rooms.append(r)
        if not rooms:
            return None
        return rng.choice(rooms)

    def _connect_rooms(self, a: Rect, b: Rect, rng: random.Random, dmap: DungeonMap) -> None:
        pa = a.center()
        pb = b.center()
        if rng.random() < 0.5:
            # horizontal then vertical
            dmap.carve_h_corridor(pa.x, pb.x, pa.y)
            dmap.carve_v_corridor(pa.y, pb.y, pb.x)
        else:
            # vertical then horizontal
            dmap.carve_v_corridor(pa.y, pb.y, pa.x)
            dmap.carve_h_corridor(pa.x, pb.x, pb.y)
        # Optionally place doors at room boundaries in future
