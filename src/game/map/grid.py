from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Generator, Iterable, List, Optional, Sequence, Tuple

from .tiles import Tile, is_walkable_tile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Size:
    width: int
    height: int


class MapGrid:
    """A safe, bounds-checked 2D tile grid for movement/collision.

    This class centralizes all grid access and provides safe methods that never
    cause index errors due to out-of-bounds coordinates. Movement and collision
    systems should rely on these methods instead of indexing the internal data
    structures directly.
    """

    __slots__ = ("_w", "_h", "_tiles")

    def __init__(self, width: int, height: int, default_tile: Tile = Tile.FLOOR) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("MapGrid dimensions must be positive")
        self._w = int(width)
        self._h = int(height)
        # tiles[y][x]
        self._tiles: List[List[Tile]] = [[default_tile for _ in range(self._w)] for _ in range(self._h)]
        logger.debug("Initialized MapGrid %dx%d with default tile %s", self._w, self._h, default_tile.name)

    @property
    def size(self) -> Size:
        return Size(self._w, self._h)

    @property
    def width(self) -> int:
        return self._w

    @property
    def height(self) -> int:
        return self._h

    def is_within(self, x: int, y: int) -> bool:
        """Check if coordinates are within the grid bounds.

        This method never raises and is the preferred way to guard any direct
        access to grid cells.
        """
        return 0 <= x < self._w and 0 <= y < self._h

    def get(self, x: int, y: int) -> Tile:
        """Return the tile at (x, y).

        Raises IndexError if out of bounds to make misuse obvious, but systems
        should prefer safe_get/is_walkable/is_within to avoid such cases.
        """
        if not self.is_within(x, y):
            raise IndexError(f"Coordinates out of bounds: ({x}, {y}) for grid {self._w}x{self._h}")
        return self._tiles[y][x]

    def safe_get(self, x: int, y: int) -> Optional[Tile]:
        """Safely get a tile and return None when out-of-bounds."""
        if not self.is_within(x, y):
            return None
        return self._tiles[y][x]

    def set(self, x: int, y: int, tile: Tile) -> None:
        """Set the tile at (x, y).

        Raises IndexError if out-of-bounds to signal incorrect map authoring.
        """
        if not isinstance(tile, Tile):
            raise TypeError("tile must be a Tile enum member")
        if not self.is_within(x, y):
            raise IndexError(f"Coordinates out of bounds: ({x}, {y}) for grid {self._w}x{self._h}")
        self._tiles[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        """Return True if the (x, y) coordinate is in-bounds and walkable.

        This method is safe and never raises.
        """
        tile = self.safe_get(x, y)
        if tile is None:
            return False
        return is_walkable_tile(tile)

    def neighbors(self, x: int, y: int, diagonals: bool = False) -> Generator[Tuple[int, int], None, None]:
        """Yield neighboring coordinates that are within bounds.

        Args:
            x: X coordinate
            y: Y coordinate
            diagonals: If True, include diagonal neighbors.

        Yields:
            Tuples of (nx, ny) that are valid indices within the grid.
        """
        if diagonals:
            offsets = (
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (1, -1), (-1, 1), (1, 1),
            )
        else:
            offsets = ((-1, 0), (1, 0), (0, -1), (0, 1))

        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if self.is_within(nx, ny):
                yield (nx, ny)

    @classmethod
    def from_lines(cls, lines: Sequence[str], mapping: Optional[dict[str, Tile]] = None) -> "MapGrid":
        """Create a MapGrid from an ASCII representation.

        Args:
            lines: Each string is a row. All rows must have the same length.
            mapping: Optional mapping of characters to Tile enum members.
                     Defaults: '.' -> FLOOR, '#' -> WALL, ' ' -> VOID

        Returns:
            MapGrid instance initialized with the given layout.
        """
        if not lines:
            raise ValueError("lines must not be empty")
        width = len(lines[0])
        if width == 0:
            raise ValueError("line width must be positive")
        for i, row in enumerate(lines):
            if len(row) != width:
                raise ValueError(f"All rows must have equal width; row 0 has {width}, row {i} has {len(row)}")

        default_mapping = {'.': Tile.FLOOR, '#': Tile.WALL, ' ': Tile.VOID}
        mapping = mapping or default_mapping

        grid = cls(width, len(lines), default_tile=Tile.VOID)
        for y, row in enumerate(lines):
            for x, ch in enumerate(row):
                tile = mapping.get(ch, Tile.VOID)
                grid.set(x, y, tile)
        return grid

    def to_lines(self, reverse_mapping: Optional[dict[Tile, str]] = None) -> List[str]:
        """Convert the grid to an ASCII representation (for debugging/testing)."""
        reverse_mapping = reverse_mapping or {Tile.FLOOR: '.', Tile.WALL: '#', Tile.VOID: ' '}
        rows: List[str] = []
        for y in range(self._h):
            row_chars = []
            for x in range(self._w):
                row_chars.append(reverse_mapping.get(self._tiles[y][x], '?'))
            rows.append(''.join(row_chars))
        return rows

    def __repr__(self) -> str:
        return f"MapGrid(width={self._w}, height={self._h})"
