"""
Amor Mortuorum core package.

This package provides headless domain logic for the Graveyard hub including:
- Player and item models
- Limited-stock Shop with deterministic, cycle-based restocking
- Crypt persistent storage (3 slots) across runs
- Save system for meta progression and crypt contents
- GraveyardHub service orchestrating rest, shop, and crypt interactions

UI layers (Arcade, CLI, etc.) should import and compose these services.
"""
from .models import Item, ItemCatalog, Inventory, Player
from .hub import GraveyardHub
from .shop import Shop
from .crypt import Crypt
from .save import SaveManager, SaveData
from .errors import (
    AmorError,
    InsufficientGold,
    OutOfStock,
    CryptFull,
    InvalidOperation,
    NotFound,
)

__all__ = [
    "Item",
    "ItemCatalog",
    "Inventory",
    "Player",
    "GraveyardHub",
    "Shop",
    "Crypt",
    "SaveManager",
    "SaveData",
    "AmorError",
    "InsufficientGold",
    "OutOfStock",
    "CryptFull",
    "InvalidOperation",
    "NotFound",
]
