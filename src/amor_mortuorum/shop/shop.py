import logging
from dataclasses import dataclass
from typing import Dict, Optional

from ..economy.config import EconomyConfig
from ..economy.events import EventBus, PurchaseCompletedEvent, PurchaseFailedEvent
from ..economy.wallet import GoldWallet
from .models import ShopItem

logger = logging.getLogger(__name__)


@dataclass
class PurchaseReceipt:
    success: bool
    item_id: str
    cost: int
    message: str


class ShopService:
    """Handles purchases, spending gold via the GoldWallet.

    This skeleton focuses on gold transactions; item granting/inventory hooks
    can be integrated later.
    """

    def __init__(self, wallet: GoldWallet, event_bus: EventBus, config: Optional[EconomyConfig] = None) -> None:
        self.wallet = wallet
        self.event_bus = event_bus
        self.config = config or EconomyConfig()
        self._inventory: Dict[str, ShopItem] = {}

    def set_inventory(self, items: Dict[str, ShopItem]) -> None:
        self._inventory = dict(items)

    def get_item(self, item_id: str) -> Optional[ShopItem]:
        return self._inventory.get(item_id)

    def price_for(self, item: ShopItem) -> int:
        price = int(round(max(0, item.base_cost) * max(0.0, self.config.shop_price_modifier)))
        return price

    def purchase(self, item_id: str) -> PurchaseReceipt:
        item = self.get_item(item_id)
        if item is None:
            msg = f"Item '{item_id}' not found"
            logger.warning(msg)
            self.event_bus.emit(PurchaseFailedEvent(item_id=item_id, cost=0, reason="not_found", current_gold=self.wallet.amount))
            return PurchaseReceipt(False, item_id, 0, msg)

        cost = self.price_for(item)
        if not self.wallet.can_afford(cost):
            msg = f"Insufficient gold for '{item.name}'; cost={cost}, have={self.wallet.amount}"
            logger.info(msg)
            self.event_bus.emit(PurchaseFailedEvent(item_id=item.item_id, cost=cost, reason="insufficient_gold", current_gold=self.wallet.amount))
            return PurchaseReceipt(False, item.item_id, cost, msg)

        try:
            self.wallet.spend(cost, reason="purchase")
        except Exception as e:
            logger.exception("Unexpected error spending gold: %s", e)
            self.event_bus.emit(PurchaseFailedEvent(item_id=item.item_id, cost=cost, reason="error", current_gold=self.wallet.amount))
            return PurchaseReceipt(False, item.item_id, cost, str(e))

        # In a full implementation we would now grant the item to the player's inventory.
        self.event_bus.emit(PurchaseCompletedEvent(item_id=item.item_id, cost=cost, remaining_gold=self.wallet.amount))
        msg = f"Purchased '{item.name}' for {cost} gold"
        logger.debug(msg)
        return PurchaseReceipt(True, item.item_id, cost, msg)
