from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PrefabDef:
    """Definition of a placeable prefab entity."""

    id: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class PrefabInstance:
    """A prefab placed in the world (e.g., from a Tiled map)."""

    id: str
    x: float
    y: float
    rotation: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    source_name: Optional[str] = None  # optional: layer or map name

    def with_defaults(self, defaults: Dict[str, Any]) -> "PrefabInstance":
        merged = dict(defaults)
        merged.update(self.properties)
        return PrefabInstance(
            id=self.id,
            x=self.x,
            y=self.y,
            rotation=self.rotation,
            properties=merged,
            source_name=self.source_name,
        )
