from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Consumable(Protocol):
    """Protocol for items that can be consumed/used, possibly conditionally."""

    def use(self, *args, **kwargs) -> bool:  # pragma: no cover - protocol method
        ...


@dataclass(eq=True, frozen=True)
class Item:
    """Base item representation.

    Items are immutable descriptors; quantities and ownership are handled by
    the Inventory which stores instances of Item in a list. Stackability is
    not required for this task but present for future expansion.
    """

    id: str
    name: str
    stackable: bool = False


# Canonical item IDs used across modules
ITEM_ID_RESURRECTION_TOKEN = "resurrection_token"
