from __future__ import annotations

from typing import Dict, List

from ..core.models import Item
from ..services.crypt_service import CryptService


class CryptUI:
    """Framework-agnostic UI adapter for the Crypt feature.

    This class provides simple methods that a rendering layer (e.g., Arcade views,
    CLI, or unit tests) can call to perform actions and retrieve the current state.
    The returned values are plain structures (strings, lists, dicts) suitable for
    any presentation layer.
    """

    def __init__(self, service: CryptService) -> None:
        self.service = service

    def get_state(self) -> Dict[str, List[str]]:
        """Return display-friendly lists of item names for both crypt and inventory."""
        crypt_names = [item.name for item in self.service.list_crypt_items()]
        inv_names = [item.name for item in self.service.list_inventory_items()]
        return {"crypt": crypt_names, "inventory": inv_names}

    def store(self, inventory_index: int) -> str:
        """Attempt to store the selected inventory item into the Crypt."""
        return self.service.store_from_inventory(inventory_index)

    def withdraw(self, crypt_index: int) -> str:
        """Attempt to withdraw the selected Crypt item to inventory."""
        return self.service.withdraw_to_inventory(crypt_index)
