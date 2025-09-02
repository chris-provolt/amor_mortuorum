class SaveError(Exception):
    """Base exception for save/load errors."""


class SaveValidationError(SaveError):
    """Raised when validation of save data fails."""


class SaveNotAllowed(SaveError):
    """Raised when an operation is not allowed per save policy (e.g., not in Graveyard)."""


class CorruptSaveError(SaveError):
    """Raised when save files are corrupted and cannot be recovered from backup."""
