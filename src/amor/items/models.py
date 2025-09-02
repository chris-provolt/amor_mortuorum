from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class ItemQuality(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Item:
    """
    Represents a game item. The structure can be extended as systems evolve.
    For this feature we primarily need an identifier, a display name, and a quality.
    """

    id: str
    name: str
    quality: ItemQuality
    # Additional metadata placeholder (stats, description, effects, etc.)
    meta: Dict[str, object] = field(default_factory=dict)

    def copy(self) -> "Item":
        # Perform a shallow copy; meta is shallow copied to avoid mutating defaults
        return Item(id=self.id, name=self.name, quality=self.quality, meta=dict(self.meta))


__all__ = ["ItemQuality", "Item"]
