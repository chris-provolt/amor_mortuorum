class AmorError(Exception):
    """Base error for Amor Mortuorum domain exceptions."""


class InsufficientGold(AmorError):
    """Raised when a player does not have enough gold to make a purchase."""


class OutOfStock(AmorError):
    """Raised when trying to buy more items than the shop currently has in stock."""


class CryptFull(AmorError):
    """Raised when attempting to deposit into a full crypt (3 slots)."""


class InvalidOperation(AmorError):
    """Raised when an operation cannot be performed in current state."""


class NotFound(AmorError):
    """Raised when requested entity (item/slot) cannot be found."""
