from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Dict

from .models import ItemCatalog, Player
from .errors import OutOfStock
from .config import DEFAULT_SHOP_POOL

logger = logging.getLogger(__name__)


@dataclass
class StockEntry:
    price: int
    quantity: int


class Shop:
    """Limited-stock shop with deterministic per-cycle restocking.

    Restock is determined by a seed and a cycle number so that the same cycle
    yields the same stock composition if needed (e.g., for testing or replays).
    """

    def __init__(self, catalog: ItemCatalog | None = None):
        self.catalog = catalog or ItemCatalog()
        self._stock: Dict[str, StockEntry] = {}
        self.cycle_id: int = -1

    def stock(self) -> Dict[str, StockEntry]:
        return dict(self._stock)

    def restock(self, seed: int, cycle: int, pool: Dict[str, Dict] | None = None) -> None:
        pool = pool or DEFAULT_SHOP_POOL
        rng = random.Random((seed << 16) ^ cycle)
        new_stock: Dict[str, StockEntry] = {}
        for item_id, spec in pool.items():
            if item_id not in self.catalog._items:
                logger.warning("Shop pool contains unknown item '%s'", item_id)
                continue
            low, high = spec["qty_range"]
            qty = rng.randint(low, high)
            price = int(spec["price"])
            if qty <= 0:
                continue
            new_stock[item_id] = StockEntry(price=price, quantity=qty)
        self._stock = new_stock
        self.cycle_id = cycle
        logger.debug("Restocked shop for cycle %s: %s", cycle, self._stock)

    def buy(self, player: Player, item_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if item_id not in self._stock:
            raise OutOfStock(f"Item '{item_id}' is not available this cycle")
        entry = self._stock[item_id]
        if entry.quantity < quantity:
            raise OutOfStock(
                f"Only {entry.quantity}x of '{item_id}' left in stock; requested {quantity}"
            )
        total_price = entry.price * quantity
        # Spend gold (raises InsufficientGold if not enough)
        player.spend_gold(total_price)
        # Add to inventory
        item = self.catalog.get(item_id)
        player.inventory.add(item, quantity)
        # Reduce stock
        entry.quantity -= quantity
        if entry.quantity == 0:
            del self._stock[item_id]
        logger.debug(
            "Purchase complete: %sx %s for %s gold; remaining stock: %s",
            quantity,
            item_id,
            total_price,
            entry.quantity if item_id in self._stock else 0,
        )
