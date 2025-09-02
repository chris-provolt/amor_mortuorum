import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import List, Set, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

# Capacity of the persistent Crypt (number of items)
CRYPT_CAPACITY = 3


@dataclass
class MetaState:
    """Represents the persistent meta-progression state.

    Attributes:
        crypt: A list of item IDs stored persistently (bank up to CRYPT_CAPACITY).
        relics_found: A set of relic IDs (strings) representing the meta collectibles found.
    """

    crypt: List[str] = field(default_factory=list)
    relics_found: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the state into a serializable dictionary for JSON persistence."""
        return {
            "version": 1,
            "crypt": list(self.crypt),
            "relics_found": sorted(list(self.relics_found)),
        }

    @classmethod
    def defaults(cls) -> "MetaState":
        """Return a default MetaState."""
        return cls(crypt=[], relics_found=set())


class SaveSystem:
    """Save system for meta-progression persistence.

    Persists a meta.json file containing:
      - crypt: up to 3 item IDs persistently stored across runs
      - relics_found: set/list of relic IDs collected

    The file is stored in {save_dir}/meta.json, where save_dir defaults to
    the environment variable AMOR_SAVE_DIR or a local 'saves' directory.

    The system is robust to file corruption and schema drift: it resets to
    safe defaults and overwrites the meta file if invalid JSON or invalid
    schema is detected.
    """

    def __init__(self, save_dir: Optional[Union[str, Path]] = None, crypt_capacity: int = CRYPT_CAPACITY) -> None:
        self._lock = RLock()
        self._crypt_capacity = int(crypt_capacity) if crypt_capacity and crypt_capacity > 0 else CRYPT_CAPACITY

        if save_dir is None:
            save_dir = os.getenv("AMOR_SAVE_DIR", "saves")
        self._save_dir = Path(save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)

        self._meta_path = self._save_dir / "meta.json"
        self._meta: Optional[MetaState] = None

    # Public API

    def load_meta(self) -> MetaState:
        """Load meta from disk, resetting to defaults if missing or corrupt.

        Returns the in-memory MetaState instance.
        """
        with self._lock:
            if self._meta is not None:
                return self._meta

            if not self._meta_path.exists():
                logger.info("meta.json not found. Creating with defaults at %s", self._meta_path)
                self._meta = MetaState.defaults()
                self._write_meta_unlocked()
                return self._meta

            # Try reading existing meta.json
            try:
                with self._meta_path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
            except Exception as exc:
                logger.warning("Failed to read meta.json (%s). Resetting to defaults.", exc)
                self._meta = MetaState.defaults()
                self._write_meta_unlocked()
                return self._meta

            validated = self._validate_and_coerce(raw)
            if validated is None:
                logger.warning("Invalid meta.json schema. Resetting to defaults.")
                self._meta = MetaState.defaults()
                self._write_meta_unlocked()
            else:
                self._meta = validated
            return self._meta

    def save_meta(self, state: Optional[MetaState] = None) -> None:
        """Persist the current or provided MetaState to disk atomically."""
        with self._lock:
            if state is not None:
                self._meta = state
            if self._meta is None:
                self._meta = MetaState.defaults()
            self._write_meta_unlocked()

    def reset_meta(self) -> MetaState:
        """Reset meta to defaults and persist to disk."""
        with self._lock:
            self._meta = MetaState.defaults()
            self._write_meta_unlocked()
            return self._meta

    # Convenience operations (auto-persist)

    def set_crypt(self, items: List[str]) -> List[str]:
        """Replace the crypt contents with the provided items (truncated to capacity).

        Automatically persists the change. Returns the new crypt list.
        """
        with self._lock:
            meta = self.load_meta()
            sanitized = self._sanitize_crypt(items)
            meta.crypt = sanitized
            self._write_meta_unlocked()
            return list(meta.crypt)

    def add_to_crypt(self, item_id: str) -> bool:
        """Add an item to the crypt if capacity allows; persists on success.

        Returns True if the item was added, False if the crypt is full or item_id invalid.
        """
        if not isinstance(item_id, str) or not item_id:
            return False
        with self._lock:
            meta = self.load_meta()
            if len(meta.crypt) >= self._crypt_capacity:
                return False
            meta.crypt.append(item_id)
            self._write_meta_unlocked()
            return True

    def clear_crypt(self) -> None:
        """Clear the crypt items and persist."""
        with self._lock:
            meta = self.load_meta()
            meta.crypt = []
            self._write_meta_unlocked()

    def add_relic(self, relic_id: str) -> bool:
        """Add a relic id to the found set; persists on change.

        Returns True if added, False if already present or invalid input.
        """
        if not isinstance(relic_id, str) or not relic_id:
            return False
        with self._lock:
            meta = self.load_meta()
            if relic_id in meta.relics_found:
                return False
            meta.relics_found.add(relic_id)
            self._write_meta_unlocked()
            return True

    def remove_relic(self, relic_id: str) -> bool:
        """Remove a relic id from the found set; persists on change.

        Returns True if removed, False if not present.
        """
        if not isinstance(relic_id, str) or not relic_id:
            return False
        with self._lock:
            meta = self.load_meta()
            if relic_id not in meta.relics_found:
                return False
            meta.relics_found.remove(relic_id)
            self._write_meta_unlocked()
            return True

    # Internal helpers

    def _write_meta_unlocked(self) -> None:
        """Atomically write the current meta to disk. Caller must hold lock."""
        assert self._meta is not None, "_write_meta_unlocked called with no meta state"
        data = self._meta.to_dict()
        tmp_path = self._meta_path.with_suffix(self._meta_path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._meta_path)
        finally:
            # Clean up temp file on any error
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    def _validate_and_coerce(self, raw: Dict[str, Any]) -> Optional[MetaState]:
        """Validate raw JSON dict and coerce into a MetaState, or return None if invalid."""
        if not isinstance(raw, dict):
            return None

        # version is optional but should be int if present
        version = raw.get("version")
        if version is not None and not isinstance(version, int):
            return None

        raw_crypt = raw.get("crypt", [])
        raw_relics = raw.get("relics_found", [])

        if not isinstance(raw_crypt, list) or not all(isinstance(x, str) for x in raw_crypt):
            return None
        if not isinstance(raw_relics, list) or not all(isinstance(x, str) for x in raw_relics):
            return None

        crypt = self._sanitize_crypt(raw_crypt)
        relics = set(raw_relics)

        return MetaState(crypt=crypt, relics_found=relics)

    def _sanitize_crypt(self, items: List[str]) -> List[str]:
        """Ensure crypt items are valid strings and within capacity."""
        cleaned = [x for x in items if isinstance(x, str) and x]
        if len(cleaned) > self._crypt_capacity:
            cleaned = cleaned[: self._crypt_capacity]
        return cleaned

    # Properties

    @property
    def meta_path(self) -> Path:
        return self._meta_path

    @property
    def save_dir(self) -> Path:
        return self._save_dir
