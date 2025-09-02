from __future__ import annotations

import logging
from typing import Callable, List, Optional, Tuple

from ..dungeon.generator import DungeonGenerator
from ..dungeon.map import DungeonMap, Point
from ..dungeon.tiles import TileType
from .events import GameEvent

logger = logging.getLogger(__name__)


class GameState:
    """Holds current run state: floor, map, and player position.

    Provides movement methods with collision against the tilemap and triggers
    floor descent when stepping onto stairs.
    """

    def __init__(self, seed: Optional[int] = None, map_width: int = 32, map_height: int = 18):
        self._listeners: List[Callable[[GameEvent, "GameState"], None]] = []
        self._generator = DungeonGenerator(seed)
        self.map_width = map_width
        self.map_height = map_height
        self.floor: int = 1
        self.map: DungeonMap = self._generator.generate(self.floor, self.map_width, self.map_height)
        if not self.map.spawn:
            raise RuntimeError("Generated map missing spawn point")
        self.player: Point = Point(self.map.spawn.x, self.map.spawn.y)
        logger.info("Initialized GameState at floor %d, player at %s", self.floor, self.player)

    def add_listener(self, listener: Callable[[GameEvent, "GameState"], None]) -> None:
        """Subscribe to game events (movement, floor change)."""
        self._listeners.append(listener)

    def _emit(self, event: GameEvent) -> None:
        for l in list(self._listeners):
            try:
                l(event, self)
            except Exception as ex:  # pragma: no cover - listeners shouldn't crash engine
                logger.exception("Listener errored on %s: %s", event, ex)

    @property
    def player_pos(self) -> Tuple[int, int]:
        return self.player.x, self.player.y

    def can_move(self, dx: int, dy: int) -> bool:
        if dx == 0 and dy == 0:
            return False
        if abs(dx) + abs(dy) != 1:
            # Only cardinal movement allowed
            return False
        nx = self.player.x + dx
        ny = self.player.y + dy
        if not self.map.in_bounds(nx, ny):
            return False
        return self.map.is_walkable(nx, ny)

    def move(self, dx: int, dy: int) -> bool:
        """Attempt to move the player by (dx, dy).

        Returns True if the move happened (walkable, in-bounds, cardinal), else False.
        If the new location is a stairs tile, automatically descends to next floor.
        """
        if not self.can_move(dx, dy):
            logger.debug("Blocked move by (%d, %d) from %s", dx, dy, self.player)
            return False
        nx = self.player.x + dx
        ny = self.player.y + dy
        self.player = Point(nx, ny)
        logger.debug("Player moved to %s", self.player)
        self._emit(GameEvent.PLAYER_MOVED)

        # Handle stairs
        tile = self.map.get(nx, ny)
        if tile.is_stairs_down:
            logger.info("Player stepped on stairs at %s; descending...", self.player)
            self._descend()
        return True

    def _descend(self) -> None:
        self.floor += 1
        self.map = self._generator.generate(self.floor, self.map_width, self.map_height)
        if not self.map.spawn:
            raise RuntimeError("Generated map missing spawn point on descent")
        self.player = Point(self.map.spawn.x, self.map.spawn.y)
        logger.info("Descended to floor %d. Player at %s", self.floor, self.player)
        self._emit(GameEvent.FLOOR_CHANGED)
