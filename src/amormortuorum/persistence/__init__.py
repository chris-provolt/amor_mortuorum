"""Persistence subsystem for Amor Mortuorum.

This package provides:
- Data models for persistent meta state (relics, crypt) and run state
- Encoding/decoding to a stable JSON schema with versioning
- A SaveManager that handles atomic disk I/O, backups, and validation

Design goals:
- Robustness: atomic writes, readable format, backups, corruption handling
- Determinism: explicit RNG seed capture, timestamps, and schema versioning
- Safety: enforce graveyard-only full saves; allow meta saves anytime
- Extensibility: migration hooks and schema version constant
"""

from .models import (
    SCHEMA_VERSION,
    Item,
    Crypt,
    RelicCollection,
    MetaState,
    RunState,
    SaveGame,
)
from .manager import SaveManager, SavePolicy
from .errors import SaveError, SaveNotAllowed, SaveValidationError, CorruptSaveError

__all__ = [
    "SCHEMA_VERSION",
    "Item",
    "Crypt",
    "RelicCollection",
    "MetaState",
    "RunState",
    "SaveGame",
    "SaveManager",
    "SavePolicy",
    "SaveError",
    "SaveNotAllowed",
    "SaveValidationError",
    "CorruptSaveError",
]
