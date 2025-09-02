from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from ..tiles import MapGrid


class DungeonGenerator(ABC):
    """Abstract base for dungeon generators."""

    @abstractmethod
    def generate(self, width: int, height: int, seed: Optional[int] = None) -> MapGrid:
        """Generate a dungeon map."""
        raise NotImplementedError
