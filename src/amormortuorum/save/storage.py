from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from .model import SaveMeta

logger = logging.getLogger(__name__)


class SaveStorage:
    """Filesystem-backed storage for saves and meta.

    Handles atomic writes to avoid partial/corrupt files and ensures directories
    exist. If your application needs multiple slots, extend this class with slot
    naming or use separate subdirectories.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.save_dir = self.root / "save"
        self.meta_path = self.save_dir / "meta.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def write_meta(self, meta: SaveMeta) -> None:
        """Write meta.json atomically.

        Raises OSError/IOError on failure.
        """
        tmp_path = self.meta_path.with_suffix(".json.tmp")
        payload = meta.to_json(indent=2)
        logger.debug("Writing meta to temporary file: %s", tmp_path)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        logger.debug("Replacing %s with %s", self.meta_path, tmp_path)
        os.replace(tmp_path, self.meta_path)

    def read_meta(self) -> Optional[SaveMeta]:
        if not self.meta_path.exists():
            return None
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = f.read()
            return SaveMeta.from_json(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to read meta: %s", exc)
            return None
