from __future__ import annotations

from dataclasses import dataclass

from amor.player.inventory import Inventory


@dataclass
class Player:
    """
    Minimal Player model for this feature: holds an inventory.
    """

    inventory: Inventory


__all__ = ["Player"]
