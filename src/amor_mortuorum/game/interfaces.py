from __future__ import annotations

from typing import Protocol


class InventoryProtocol(Protocol):
    """Protocol that any inventory implementation must follow.

    This protocol is intentionally small and focused on the needs of
    interactables like doors. Implementations can expand however they like
    as long as these methods remain available.
    """

    def get_item_count(self, item_id: str) -> int:
        """Return the count of the item currently held.

        Args:
            item_id: Unique identifier for the item type (e.g., "key").
        """

    def consume_item(self, item_id: str, qty: int = 1) -> None:
        """Consume a quantity of the specified item.

        Should raise a ValueError if insufficient quantity is available.
        """


class HasInventory(Protocol):
    """Actors that expose an inventory via a property."""

    @property
    def inventory(self) -> InventoryProtocol:  # pragma: no cover - type contract
        ...


def get_inventory_from(actor: object) -> InventoryProtocol:
    """Adapt an object to InventoryProtocol if possible.

    Supports two styles:
    - The actor itself implements InventoryProtocol
    - The actor has an `.inventory` property that implements InventoryProtocol

    Raises:
        TypeError: If no compatible inventory can be found.
    """
    # Direct implementation
    if hasattr(actor, "get_item_count") and hasattr(actor, "consume_item"):
        return actor  # type: ignore[return-value]

    # Actor with inventory property
    inv = getattr(actor, "inventory", None)
    if inv and hasattr(inv, "get_item_count") and hasattr(inv, "consume_item"):
        return inv  # type: ignore[return-value]

    raise TypeError(
        f"Object {actor!r} does not implement InventoryProtocol nor expose an 'inventory' implementing it."
    )
