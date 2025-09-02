from dataclasses import dataclass
from typing import List, Optional, Tuple, Iterable


@dataclass
class Tile:
    """Map tile flags."""
    blocking: bool = False


class GridMap:
    """Simple orthogonal tile map supporting walls/LOS and entity lookup."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Invalid map size")
        self.width = width
        self.height = height
        self.tiles: List[List[Tile]] = [[Tile(blocking=False) for _ in range(height)] for _ in range(width)]
        # Dynamic actor registry maintained by GameState
        self._entities: List["Actor"] = []  # type: ignore[name-defined]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocking(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return True  # Out of bounds acts as wall
        return self.tiles[x][y].blocking

    def set_wall(self, x: int, y: int, blocking: bool = True) -> None:
        if not self.in_bounds(x, y):
            raise IndexError("Position out of bounds")
        self.tiles[x][y].blocking = blocking

    # Entity management hooks (called by GameState)
    def register_entity(self, entity: "Actor") -> None:  # type: ignore[name-defined]
        self._entities.append(entity)

    def unregister_entity(self, entity: "Actor") -> None:  # type: ignore[name-defined]
        if entity in self._entities:
            self._entities.remove(entity)

    def entities_at(self, x: int, y: int) -> List["Actor"]:  # type: ignore[name-defined]
        return [e for e in self._entities if e.x == x and e.y == y]

    def raycast(self, start: Tuple[int, int], direction: Tuple[int, int], max_range: int) -> Iterable[Tuple[int, int]]:
        """Yield each tile coordinate along a ray until blocked or range reached.

        Includes the first tile in front of start; does not include start itself.
        Stops before (and not including) a blocking tile position.
        """
        sx, sy = start
        dx, dy = direction
        cx, cy = sx, sy
        for _ in range(max_range):
            cx += dx
            cy += dy
            if not self.in_bounds(cx, cy):
                break
            if self.is_blocking(cx, cy):
                break
            yield (cx, cy)

    def find_first_entity_in_line(self, start: Tuple[int, int], direction: Tuple[int, int], max_range: int,
                                   exclude_eid: Optional[str] = None) -> Optional["Actor"]:  # type: ignore[name-defined]
        for (x, y) in self.raycast(start, direction, max_range):
            ents = self.entities_at(x, y)
            for e in ents:
                if exclude_eid is not None and e.eid == exclude_eid:
                    continue
                return e
        return None

    def has_line_of_sight(self, start: Tuple[int, int], target: Tuple[int, int]) -> bool:
        sx, sy = start
        tx, ty = target
        if sx != tx and sy != ty:
            return False  # only cardinal LOS allowed for dart traps
        dx = 0 if sx == tx else (1 if tx > sx else -1)
        dy = 0 if sy == ty else (1 if ty > sy else -1)
        cx, cy = sx, sy
        # Step until next cell equals target; if blocking found, no LOS
        while True:
            cx += dx
            cy += dy
            if (cx, cy) == (tx, ty):
                return not self.is_blocking(cx, cy)
            if self.is_blocking(cx, cy):
                return False

