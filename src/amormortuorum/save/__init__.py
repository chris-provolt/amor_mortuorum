"""
Save system for Amor Mortuorum.

This package provides a storage layer, data models, and a SaveManager that
coordinates enforcement rules (e.g., Graveyard-only saves) and user feedback.
"""
from .model import SaveMeta
from .manager import SaveManager, SaveResult
from .storage import SaveStorage

__all__ = ["SaveMeta", "SaveManager", "SaveResult", "SaveStorage"]
