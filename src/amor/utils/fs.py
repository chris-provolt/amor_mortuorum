from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def ensure_dir(path: Path, *, mode: int = 0o700) -> None:
    """Ensure directory exists with secure permissions."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except Exception:  # Platform may not support
        logger.debug("Could not chmod directory: %s", path, exc_info=True)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write bytes to a path using a temporary file and replace.

    Ensures that either the old file remains or the new file fully replaces it.
    """
    tmp_dir = path.parent
    ensure_dir(tmp_dir)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            logger.debug("Could not remove temp file %s", tmp_name, exc_info=True)


def atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    data = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    atomic_write_bytes(path, data)
