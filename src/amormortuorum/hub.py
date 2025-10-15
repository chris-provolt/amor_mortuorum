from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .models import Player, ItemCatalog
from .shop import Shop
from .crypt import Crypt
from .save import SaveManager, SaveData

logger = logging.getLogger(__name__)


@dataclass
class HubContext:
    save: SaveData
    shop: Shop
    crypt: Crypt


class GraveyardHub:
    """Graveyard Hub service: rest, shop, crypt management.

    Life-cycle:
    - Construct with a SaveManager (optionally pointing to a custom root dir)
    - Call enter() per visit to the Graveyard to restock the shop deterministically
    - Use rest(), shop.buy(), crypt.deposit()/withdraw() as needed
    - All crypt changes persist via SaveManager.save()
    """

    def __init__(
        self,
        save_manager: Optional[SaveManager] = None,
        catalog: Optional[ItemCatalog] = None,
    ) -> None:
        self.save_manager = save_manager or SaveManager()
        self.catalog = catalog or ItemCatalog()
        self._ctx: Optional[HubContext] = None

    def enter(self) -> HubContext:
        save = self.save_manager.load()
        save.hub_cycle += 1
        shop = Shop(self.catalog)
        shop.restock(seed=save.meta_seed, cycle=save.hub_cycle)
        crypt = Crypt(save, self.catalog)
        self._ctx = HubContext(save=save, shop=shop, crypt=crypt)
        # Persist cycle increment immediately
        self.save_manager.save(save)
        logger.info("Entered Graveyard hub: cycle=%s", save.hub_cycle)
        return self._ctx

    @property
    def ctx(self) -> HubContext:
        if self._ctx is None:
            raise RuntimeError("Hub not entered. Call enter() first.")
        return self._ctx

    def rest(self, player: Player) -> None:
        player.heal_full()
        logger.info("Player rested at the Graveyard and is fully healed.")

    # Convenience wrappers that also persist crypt changes
    def crypt_deposit(self, player: Player, item_id: str, quantity: int = 1) -> None:
        self.ctx.crypt.deposit(player, item_id, quantity)
        self.save_manager.save(self.ctx.save)

    def crypt_withdraw(self, player: Player, slot_index: int, quantity: Optional[int] = None) -> None:
        self.ctx.crypt.withdraw(player, slot_index, quantity)
        self.save_manager.save(self.ctx.save)

    def snapshot(self) -> SaveData:
        """Return a snapshot of current save/meta state."""
        return self.ctx.save
