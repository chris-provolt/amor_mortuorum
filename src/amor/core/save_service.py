import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _atomic_write(file_path: str, data: str) -> None:
    """Safely write data to a file using an atomic replace.

    This minimizes the risk of partial writes or corruption.
    """
    directory = os.path.dirname(file_path)
    _ensure_dir(directory)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, file_path)


@dataclass
class SaveService:
    """Simple JSON-backed save service with sectioned storage.

    The save data is structured as a dict of sections, e.g.:
    {
      "schema_version": 1,
      "relics": {"collected": ["id1", "id2"], "version": 1},
      "meta": {...}
    }

    Thread-safe for in-process usage.
    """

    save_root: str
    namespace: str = "player"
    schema_version: int = 1
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    @property
    def save_path(self) -> str:
        return os.path.join(self.save_root, f"{self.namespace}.save.json")

    def _load_raw(self) -> Dict[str, Any]:
        if not os.path.exists(self.save_path):
            logger.debug("Save file does not exist: %s", self.save_path)
            return {"schema_version": self.schema_version}
        try:
            with open(self.save_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if not isinstance(data, dict):
                    raise ValueError("Save file malformed: not a dict")
                return data
        except Exception as e:
            logger.error("Failed to load save file %s: %s", self.save_path, e)
            # In case of corruption, return a minimal structure instead of crashing.
            return {"schema_version": self.schema_version}

    def _write_raw(self, data: Dict[str, Any]) -> None:
        try:
            payload = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
            _atomic_write(self.save_path, payload)
        except Exception as e:
            logger.exception("Failed to write save file %s: %s", self.save_path, e)
            raise

    def get_section(self, name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            store = self._load_raw()
            sec = store.get(name)
            if isinstance(sec, dict):
                return sec
            return {} if default is None else default

    def update_section(self, name: str, update: Dict[str, Any]) -> Dict[str, Any]:
        """Read-modify-write update of a named section.

        Returns: the updated section dict.
        """
        with self._lock:
            store = self._load_raw()
            section = store.get(name) or {}
            if not isinstance(section, dict):
                section = {}
            section.update(update)
            store[name] = section
            store.setdefault("schema_version", self.schema_version)
            self._write_raw(store)
            return section

    def merge_into_section(self, name: str, merge: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-merge keys in a section (1-level deep); creates section if absent."""
        with self._lock:
            store = self._load_raw()
            section = store.get(name) or {}
            if not isinstance(section, dict):
                section = {}
            for k, v in merge.items():
                section[k] = v
            store[name] = section
            store.setdefault("schema_version", self.schema_version)
            self._write_raw(store)
            return section
