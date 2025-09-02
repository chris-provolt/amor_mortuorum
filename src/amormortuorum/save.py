from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_paths

logger = logging.getLogger(__name__)

SAVE_VERSION = 1


@dataclass
class CryptSlot:
    item_id: str
    quantity: int


@dataclass
class SaveData:
    version: int = SAVE_VERSION
    meta_seed: int = 1337
    hub_cycle: int = 0
    crypt: List[CryptSlot] = field(default_factory=list)
    relics: List[str] = field(default_factory=list)
    gold_bank: int = 0  # placeholder for future meta-gold

    def to_json(self) -> Dict:
        return {
            "version": self.version,
            "meta_seed": self.meta_seed,
            "hub_cycle": self.hub_cycle,
            "crypt": [asdict(s) for s in self.crypt],
            "relics": self.relics,
            "gold_bank": self.gold_bank,
        }

    @classmethod
    def from_json(cls, data: Dict) -> "SaveData":
        if data.get("version") != SAVE_VERSION:
            logger.warning(
                "Save version mismatch: expected %s, got %s; attempting to load",
                SAVE_VERSION,
                data.get("version"),
            )
        crypt_slots = [CryptSlot(**s) for s in data.get("crypt", [])]
        return cls(
            version=data.get("version", SAVE_VERSION),
            meta_seed=int(data.get("meta_seed", 1337)),
            hub_cycle=int(data.get("hub_cycle", 0)),
            crypt=crypt_slots,
            relics=list(data.get("relics", [])),
            gold_bank=int(data.get("gold_bank", 0)),
        )


class SaveManager:
    """Manages on-disk persistence of meta state (crypt, relics, cycles).

    Uses an atomic write strategy to prevent corruption: write to a temporary
    file then os.replace to the target path.
    """

    def __init__(self, root: Optional[Path] = None):
        self.paths = get_paths(root)
        self.paths.save_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[SaveData] = None

    @property
    def save_path(self) -> Path:
        return self.paths.save_file

    def load(self) -> SaveData:
        if self._cache is not None:
            return self._cache
        if not self.save_path.exists():
            logger.info("No save file found; creating new SaveData")
            self._cache = SaveData()
            self._atomic_write(self._cache.to_json())
            return self._cache
        with self.save_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        self._cache = SaveData.from_json(raw)
        return self._cache

    def save(self, data: SaveData) -> None:
        self._cache = data
        self._atomic_write(data.to_json())

    def _atomic_write(self, payload: Dict) -> None:
        tmp_path = self.save_path.with_suffix(self.save_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp_path, self.save_path)
        logger.debug("Atomic save written to %s", self.save_path)
