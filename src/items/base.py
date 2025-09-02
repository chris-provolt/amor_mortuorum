from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Item:
    """Base item type.

    Items may be stackable in the future; for now, every item is unique by instance.
    """

    id: str
    name: str
    description: str = ""

    def __hash__(self) -> int:  # pragma: no cover - identity hash
        return id(self)
