class ShopError(Exception):
    """Base class for shop-related errors."""


class InsufficientFundsError(ShopError):
    """Raised when a purchase cannot be completed due to insufficient gold."""


class OutOfStockError(ShopError):
    """Raised when attempting to buy more units than available in stock."""


class UnknownItemError(ShopError):
    """Raised when an item id is not found in the shop inventory."""


class ValidationError(ShopError):
    """Raised when provided inputs or data files are invalid."""
