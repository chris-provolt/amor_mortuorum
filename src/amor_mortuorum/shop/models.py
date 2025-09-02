from dataclasses import dataclass


@dataclass(frozen=True)
class ShopItem:
    item_id: str
    name: str
    base_cost: int
