from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import List

from ..core.errors import PersistenceError
from ..core.models import Item, Crypt

logger = logging.getLogger(__name__)


class SaveManager(ABC):
    """Abstract interface for Crypt persistence."""

    @abstractmethod
    def load_crypt(self, default_capacity: int) -> Crypt:
        """Load a Crypt from storage. If none exists, return an empty Crypt with the given capacity."""

    @abstractmethod
    def save_crypt(self, crypt: Crypt) -> None:
        """Persist the Crypt to storage."""


class LocalJSONSaveManager(SaveManager):
    """SaveManager implementation using a local JSON file.

    File structure:
    {
      "version": 1,
      "crypt": {
         "capacity": 3,
         "items": [{"id": "potion", "name": "Potion"}, ...]
      }
    }
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_crypt(self, default_capacity: int) -> Crypt:
        if not self.path.exists():
            logger.info("Crypt save file not found; initializing new Crypt with capacity %s", default_capacity)
            return Crypt(capacity=default_capacity)
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            crypt_data = data.get("crypt", {"capacity": default_capacity, "items": []})
            crypt = Crypt.from_dict(crypt_data)
            # Ensure capacity is at least default (never shrink automatically)
            if crypt.capacity < default_capacity:
                crypt.capacity = default_capacity
            return crypt
        except Exception as exc:  # noqa: BLE001 broad but wrapped
            logger.exception("Failed to load Crypt from %s", self.path)
            raise PersistenceError(str(exc)) from exc

    def save_crypt(self, crypt: Crypt) -> None:
        try:
            payload = {"version": 1, "crypt": crypt.to_dict()}
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save Crypt to %s", self.path)
            raise PersistenceError(str(exc)) from exc


class InMemorySaveManager(SaveManager):
    """Test/deterministic SaveManager that holds data in memory only."""

    def __init__(self) -> None:
        self._crypt_data: dict | None = None

    def load_crypt(self, default_capacity: int) -> Crypt:
        if self._crypt_data is None:
            return Crypt(capacity=default_capacity)
        return Crypt.from_dict(self._crypt_data)

    def save_crypt(self, crypt: Crypt) -> None:
        self._crypt_data = crypt.to_dict()
