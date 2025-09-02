from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal

from .effects import Effect

TargetKind = Literal["self", "ally", "ally_or_self", "enemy"]
ItemKind = Literal["potion", "scroll"]


@dataclass
class ItemDefinition:
    """Data model for an item defininition used in combat."""

    id: str
    name: str
    kind: ItemKind
    target: TargetKind
    effects: List[Effect] = field(default_factory=list)

    def is_potion(self) -> bool:
        return self.kind == "potion"

    def is_scroll(self) -> bool:
        return self.kind == "scroll"
