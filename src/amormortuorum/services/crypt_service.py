from __future__ import annotations

import logging
from typing import List

from ..configs.defaults import CRYPT_CAPACITY
from ..core.errors import CryptFullError, InvalidIndexError
from ..core.models import Crypt, Inventory, Item
from ..persistence.save_manager import SaveManager

logger = logging.getLogger(__name__)


class CryptService:
    """Application service for Crypt operations and integration with Inventory and persistence.

    This layer encapsulates the domain rules (capacity, movement between lists), handles
    persistence after mutations, and provides user-facing status messages expected by the UI.
    """

    def __init__(self, inventory: Inventory, save_manager: SaveManager | None = None, capacity: int | None = None) -> None:
        self.inventory = inventory
        self.save_manager = save_manager
        self._capacity = capacity or CRYPT_CAPACITY
        self.crypt: Crypt = self._load_or_init_crypt()

    # ---- Internal helpers ----
    def _load_or_init_crypt(self) -> Crypt:
        if self.save_manager is None:
            logger.info("No SaveManager provided; using ephemeral Crypt state")
            return Crypt(capacity=self._capacity)
        crypt = self.save_manager.load_crypt(default_capacity=self._capacity)
        # Guarantee capacity matches configured capacity (do not reduce if larger)
        if crypt.capacity < self._capacity:
            crypt.capacity = self._capacity
        return crypt

    def _persist(self) -> None:
        if self.save_manager is not None:
            self.save_manager.save_crypt(self.crypt)

    # ---- Query operations ----
    def list_crypt_items(self) -> List[Item]:
        return self.crypt.list_items()

    def list_inventory_items(self) -> List[Item]:
        return self.inventory.list_items()

    # ---- Commands ----
    def store_from_inventory(self, inventory_index: int) -> str:
        """Attempt to move an item at inventory_index into the Crypt.

        Returns a user-facing status message. On capacity full, returns exactly 'Crypt full'.
        """
        # Check capacity first to avoid mutating inventory when Crypt is full
        if not self.crypt.can_store():
            logger.debug("Store attempt failed: crypt at capacity %s", self.crypt.capacity)
            return "Crypt full"
        try:
            item = self.inventory.remove_index(inventory_index)
        except InvalidIndexError:
            logger.debug("Store attempt failed: invalid inventory index %s", inventory_index)
            return "Invalid selection"
        try:
            self.crypt.store_item(item)
        except CryptFullError:
            # Extremely unlikely because of the can_store guard, but keep safe
            # Put the item back into inventory to avoid loss
            self.inventory.add_item(item)
            logger.warning("Race condition: crypt full after removal; item returned to inventory")
            return "Crypt full"
        self._persist()
        logger.info("Stored item '%s' into Crypt", item.name)
        return f"Stored {item.name} in Crypt."

    def withdraw_to_inventory(self, crypt_index: int) -> str:
        """Move an item out of the Crypt into inventory. Returns a status message."""
        try:
            item = self.crypt.withdraw_index(crypt_index)
        except InvalidIndexError:
            logger.debug("Withdraw attempt failed: invalid crypt index %s", crypt_index)
            return "Invalid selection"
        self.inventory.add_item(item)
        self._persist()
        logger.info("Withdrew item '%s' from Crypt to inventory", item.name)
        return f"Withdrew {item.name} to inventory."

    def reset_crypt(self) -> None:
        """Utility to clear crypt items (not part of UI, helpful for tests or run resets)."""
        self.crypt = Crypt(capacity=self._capacity)
        self._persist()
