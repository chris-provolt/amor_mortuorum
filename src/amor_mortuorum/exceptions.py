class AmorMortuorumError(Exception):
    """Base exception for the Amor Mortuorum project."""


class InventoryError(AmorMortuorumError):
    """Raised when inventory operations fail (e.g., out of stock)."""


class CombatError(AmorMortuorumError):
    """Raised for combat related errors."""


class ItemUseError(CombatError):
    """Raised when an item cannot be used in combat (invalid target, etc.)."""
