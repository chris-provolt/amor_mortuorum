"""Limited-stock shop with deterministic per-cycle restocking."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Dict, Optional

from ..data import GameData, ShopEntry
from ..errors import OutOfStock
from .entities import Player

logger = logging.getLogger(__name__)


@dataclass
class StockEntry:
    price: int
    quantity: int


class Shop:
    """Stock is a pure function of ``(seed, cycle)`` so a Graveyard visit replays identically."""

    def __init__(self, data: GameData):
        self.data = data
        self._stock: Dict[str, StockEntry] = {}
        self.cycle_id: int = -1

    def stock(self) -> Dict[str, StockEntry]:
        return {k: StockEntry(v.price, v.quantity) for k, v in self._stock.items()}

    def restock(
        self, seed: int, cycle: int, pool: Optional[Dict[str, ShopEntry]] = None
    ) -> None:
        pool = pool if pool is not None else self.data.shop_pool
        rng = random.Random((seed << 16) ^ cycle)
        new_stock: Dict[str, StockEntry] = {}
        for item_id, spec in pool.items():
            if not self.data.has_item(item_id):
                logger.warning("Shop pool contains unknown item '%s'", item_id)
                continue
            low, high = spec.qty_range
            qty = rng.randint(low, high)
            if qty <= 0:
                continue
            new_stock[item_id] = StockEntry(price=int(spec.price), quantity=qty)
        self._stock = new_stock
        self.cycle_id = cycle
        logger.debug("Restocked shop for cycle %s: %s", cycle, self._stock)

    def buy(self, player: Player, item_id: str, quantity: int = 1) -> int:
        """Buy ``quantity`` of ``item_id``; returns gold spent. Raises on failure."""
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
        player.spend_gold(total_price)  # raises InsufficientGold
        try:
            player.inventory.add(self.data.item(item_id), quantity)
        except Exception:
            player.add_gold(total_price)  # refund if the bag cannot hold it
            raise
        entry.quantity -= quantity
        if entry.quantity == 0:
            del self._stock[item_id]
        logger.debug("Purchase: %sx %s for %s gold", quantity, item_id, total_price)
        return total_price
