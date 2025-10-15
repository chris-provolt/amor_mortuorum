from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AmorMortuorum"
APP_DIR_NAME = "amormortuorum"


def default_save_root() -> Path:
    """Return the default platform-specific root directory for saves.

    Linux: ~/.local/share/amormortuorum
    macOS: ~/Library/Application Support/AmorMortuorum
    Windows: %APPDATA%\\AmorMortuorum
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if not base:
            base = Path.home() / "AppData" / "Roaming"
        else:
            base = Path(base)
        return base / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux and others
        return Path.home() / ".local" / "share" / APP_DIR_NAME


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
