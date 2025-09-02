from __future__ import annotations

from amormortuorum.models.item import Item, ITEM_ID_RESURRECTION_TOKEN


def create_resurrection_token() -> Item:
    """Factory to create a Resurrection Token item.

    In a fuller implementation, this would likely load from data definitions.
    """
    return Item(id=ITEM_ID_RESURRECTION_TOKEN, name="Resurrection Token", stackable=True)
