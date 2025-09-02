from __future__ import annotations

class CryptFullError(Exception):
    """Raised when attempting to store an item while the Crypt is at capacity."""


class InvalidIndexError(Exception):
    """Raised when a list index selection is invalid/out of range."""


class PersistenceError(Exception):
    """Raised when persistence (save/load) operations fail."""
