from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from game.map.grid import MapGrid

logger = logging.getLogger(__name__)


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Entity:
    """Simple entity representation for movement tests.

    In the full game this would likely be part of a more complex ECS/component
    system with additional properties (collision, speed, etc.).
    """

    id: str
    pos: Position


class CollisionMap(Protocol):
    """Protocol for map interfaces used by MovementEngine.

    This abstraction allows the engine to work with different map
    implementations as long as they provide these methods.
    """

    def is_within(self, x: int, y: int) -> bool: ...
    def is_walkable(self, x: int, y: int) -> bool: ...


class MovementEngine:
    """Handles movement attempts with safe bounds/collision checks."""

    def try_move(self, entity: Entity, dx: int, dy: int, grid: CollisionMap) -> bool:
        """Attempt to move an entity by (dx, dy) within a grid.

        The move is rejected if the target is out-of-bounds or not walkable.
        The method is safe and never raises due to index errors.

        Args:
            entity: Entity to move.
            dx: Delta X.
            dy: Delta Y.
            grid: Map grid implementing CollisionMap protocol.

        Returns:
            True if movement occurred; False if blocked.
        """
        if dx == 0 and dy == 0:
            logger.debug("No-op movement requested for entity %s", entity.id)
            return True  # No movement needed, considered success

        tx = entity.pos.x + dx
        ty = entity.pos.y + dy

        if not grid.is_within(tx, ty):
            logger.debug(
                "Blocked movement for %s: target (%d,%d) out of bounds", entity.id, tx, ty
            )
            return False

        if not grid.is_walkable(tx, ty):
            logger.debug(
                "Blocked movement for %s: target (%d,%d) not walkable", entity.id, tx, ty
            )
            return False

        logger.debug("Entity %s moves from (%d,%d) to (%d,%d)", entity.id, entity.pos.x, entity.pos.y, tx, ty)
        entity.pos.x = tx
        entity.pos.y = ty
        return True


__all__ = [
    "Position",
    "Entity",
    "MovementEngine",
]
