from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path
from typing import Optional

__all__ = [
    "APP_NAME",
    "APP_SLUG",
    "portable_mode_enabled",
    "executable_dir",
    "get_base_user_data_dir",
    "get_user_data_root",
    "get_config_dir",
    "get_save_dir",
    "get_cache_dir",
    "get_logs_dir",
    "ensure_exists",
]


# Basic app identity used for directories
APP_NAME = "Amor Mortuorum"
APP_SLUG = "amor-mortuorum"

_logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """Return True if running under a frozen bundle (e.g., PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def executable_dir() -> Path:
    """Return the directory that contains the running executable or script.

    - If frozen (PyInstaller), this is the directory of sys.executable.
    - Otherwise, use the current working directory as an anchor.
      We avoid relying on __file__ to simplify usage in different entry patterns.
    """
    if is_frozen():
        try:
            return Path(sys.executable).resolve().parent
        except Exception as exc:  # pragma: no cover - highly unlikely
            _logger.warning("Failed to resolve executable dir: %s", exc)
    # Fallback: working directory
    return Path.cwd().resolve()


def portable_mode_enabled(flag_filename: str = "portable_mode.flag") -> bool:
    """Determine if the app should use portable mode storage.

    Portable mode stores all user data alongside the executable under a
    'userdata' directory.

    Enabled if any of the following are true:
    - Environment variable AMOR_PORTABLE is set to one of: "1", "true", "yes" (case-insensitive)
    - A file named 'portable_mode.flag' exists next to the executable (or current
      working directory for non-frozen runs)

    The flag filename can be customized via the `flag_filename` argument for testing.
    """
    env = os.getenv("AMOR_PORTABLE", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    flag_path = executable_dir() / flag_filename
    return flag_path.exists()


def _windows_user_data_dir() -> Path:
    # %APPDATA% defaults to Roaming. If missing, fallback to user home.
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def _mac_user_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_NAME


def _linux_user_data_dir() -> Path:
    # Follow XDG base directory spec where applicable
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_SLUG
    return Path.home() / ".local" / "share" / APP_SLUG


def get_base_user_data_dir() -> Path:
    """Return the OS-appropriate base directory for app data (non-portable).

    Windows: %APPDATA%/Amor Mortuorum
    macOS:   ~/Library/Application Support/Amor Mortuorum
    Linux:   ~/.local/share/amor-mortuorum (or $XDG_DATA_HOME/amor-mortuorum)
    """
    system = platform.system()
    if system == "Windows":
        return _windows_user_data_dir()
    if system == "Darwin":
        return _mac_user_data_dir()
    # Treat everything else as Linux/Unix
    return _linux_user_data_dir()


def get_user_data_root(create: bool = True) -> Path:
    """Return the root directory used for all user data.

    - Portable mode: <executable_dir>/userdata
    - Non-portable: OS-specific user data dir

    When `create` is True, ensures the directory exists.
    """
    if portable_mode_enabled():
        root = executable_dir() / "userdata"
    else:
        root = get_base_user_data_dir()
    if create:
        ensure_exists(root)
    return root


def ensure_exists(path: Path) -> None:
    """Create the directory if it doesn't exist. Log and raise on failure."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pragma: no cover - IO errors are environment-specific
        _logger.error("Failed to create directory '%s': %s", path, exc)
        raise


def _subdir(name: str, create: bool = True) -> Path:
    root = get_user_data_root(create=create)
    sub = root / name
    if create:
        ensure_exists(sub)
    return sub


def get_config_dir(create: bool = True) -> Path:
    """Return directory for config files."""
    return _subdir("config", create=create)


def get_save_dir(create: bool = True) -> Path:
    """Return directory for save files (game saves, profiles)."""
    return _subdir("saves", create=create)


def get_cache_dir(create: bool = True) -> Path:
    """Return directory for caches (procedural seeds, thumbnails, etc.)."""
    return _subdir("cache", create=create)


def get_logs_dir(create: bool = True) -> Path:
    """Return directory for logs."""
    return _subdir("logs", create=create)


# Convenience: if this module is executed directly, print out the resolved paths
if __name__ == "__main__":  # pragma: no cover - manual debugging aid
    logging.basicConfig(level=logging.INFO)
    print(f"Frozen: {is_frozen()}")
    print(f"Executable dir: {executable_dir()}")
    print(f"Portable: {portable_mode_enabled()}")
    print(f"User data root: {get_user_data_root()}")
    print(f"Config dir: {get_config_dir()}")
    print(f"Saves dir: {get_save_dir()}")
    print(f"Cache dir: {get_cache_dir()}")
    print(f"Logs dir: {get_logs_dir()}")
