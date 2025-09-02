from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class MetaStore:
    """Thread-safe JSON store for meta-progression data (meta.json).

    Provides atomic load/save/update helpers and ensures the directory exists.
    """

    CURRENT_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            logger.info("meta.json not found at %s, creating with default schema", self.path)
            self.save(self._default())

    def _default(self) -> Dict[str, Any]:
        return {
            "version": self.CURRENT_VERSION,
            "relics": {
                "collected_ids": [],  # fragment ids only
                "final_collected": False,
            },
        }

    def load(self) -> Dict[str, Any]:
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                logger.debug("Loaded meta.json from %s: %r", self.path, data)
                return data
            except FileNotFoundError:
                logger.warning("meta.json missing at %s; recreating default", self.path)
                default = self._default()
                self.save(default)
                return deepcopy(default)

    def save(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            logger.debug("Saved meta.json to %s", self.path)

    def update(self, fn: Callable[[Dict[str, Any]], Dict[str, Any] | None]) -> Dict[str, Any]:
        """Atomically load, transform, and save.

        The provided function receives the current data and may modify it in-place
        or return a new dict. The resulting dict is saved and returned.
        """
        with self._lock:
            data = self.load()
            result = fn(data)
            if result is None:
                result = data
            self.save(result)
            return deepcopy(result)
