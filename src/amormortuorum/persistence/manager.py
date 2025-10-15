from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Optional

from .codec import encode_save, decode_save
from .errors import SaveError, SaveNotAllowed, CorruptSaveError, SaveValidationError
from .models import SaveGame, MetaState
from .paths import default_save_root, ensure_dir


class SavePolicy:
    """Save policy configuration.

    - meta_only: if True, only meta saves are allowed (always permitted)
    - full: full saves allowed only when run.in_graveyard is True
    - save_and_quit: future flag to allow emergency saves mid-run; default False
    """

    def __init__(self, allow_save_and_quit: bool = False) -> None:
        self.allow_save_and_quit = allow_save_and_quit


class SaveManager:
    """Responsible for reading/writing save files, enforcing policy and atomicity."""

    def __init__(self, root_dir: Optional[Path] = None, profile_id: str = "default", policy: Optional[SavePolicy] = None) -> None:
        self.root_dir = ensure_dir(root_dir or default_save_root())
        self.profile_dir = ensure_dir(self.root_dir / "profiles" / profile_id)
        self.meta_path = self.profile_dir / "meta.json"
        self.run_path = self.profile_dir / "run.json"
        self.lock = threading.RLock()
        self.policy = policy or SavePolicy()
        self.profile_id = profile_id

    # Public API

    def save_meta(self, meta: MetaState) -> Path:
        """Persist only meta state. Always allowed."""
        with self.lock:
            save = self._load_or_init_save()
            save.meta = meta
            save.touch()
            text = encode_save(save)
            self._atomic_write(self.meta_path, text)
            return self.meta_path

    def load_meta(self) -> MetaState:
        with self.lock:
            save = self._load_save_with_fallback(self.meta_path)
            return save.meta

    def save_full(self, save: SaveGame) -> None:
        """Persist both meta and run state.

        Enforces Graveyard-only saving unless allow_save_and_quit is enabled in policy.
        """
        with self.lock:
            if save.run is None:
                raise SaveValidationError("SaveGame.run must be present for full save")
            if not save.run.in_graveyard and not self.policy.allow_save_and_quit:
                raise SaveNotAllowed(
                    "Full save not allowed outside the Graveyard. Return to Graveyard or enable save-and-quit."
                )
            save.touch()
            text = encode_save(save)
            # We store a full copy for run.json too, for recovery and inspection
            self._atomic_write(self.run_path, text)
            # Also update meta.json to keep meta in sync (redundancy)
            self._atomic_write(self.meta_path, text)

    def load_full(self) -> SaveGame:
        """Load the latest save, preferring run.json, falling back to meta.json."""
        with self.lock:
            try:
                return self._load_save_with_fallback(self.run_path)
            except SaveError:
                # Fall back to meta; run state may be None
                return self._load_save_with_fallback(self.meta_path)

    # Internal utilities

    def _load_or_init_save(self) -> SaveGame:
        if self.meta_path.exists():
            return self._load_save_with_fallback(self.meta_path)
        else:
            # Initialize a new save container for this profile
            save = SaveGame(profile_id=self.profile_id)
            text = encode_save(save)
            self._atomic_write(self.meta_path, text)
            return save

    def _load_save_with_fallback(self, path: Path) -> SaveGame:
        primary_exc: Optional[Exception] = None
        try:
            return self._read_save(path)
        except Exception as e:
            primary_exc = e
            # Attempt backup recovery
            bak = path.with_suffix(path.suffix + ".bak")
            if bak.exists():
                try:
                    return self._read_save(bak)
                except Exception:
                    pass
            # Attempt to read the other file (meta <-> run) for redundancy
            try:
                alt = self.run_path if path == self.meta_path else self.meta_path
                if alt.exists():
                    return self._read_save(alt)
            except Exception:
                pass
        # If we reach here, recovery failed
        raise CorruptSaveError(f"Unable to load save from {path}: {primary_exc}")

    def _read_save(self, path: Path) -> SaveGame:
        try:
            with path.open("r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError as e:
            raise SaveError(f"Save file not found: {path}") from e
        return decode_save(text)

    def _atomic_write(self, path: Path, text: str) -> None:
        """Write text to path atomically, creating a .bak backup of the previous file.

        Strategy:
        - Write to path.tmp
        - Flush and fsync
        - Move existing path to path.bak (replace if exists)
        - Rename path.tmp to path
        This provides durability and recovery from partial writes.
        """
        tmp = path.with_suffix(path.suffix + ".tmp")
        bak = path.with_suffix(path.suffix + ".bak")
        # Ensure directory exists
        ensure_dir(path.parent)
        # Write tmp file
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        # Backup previous
        if path.exists():
            # Replace existing backup
            try:
                if bak.exists():
                    bak.unlink()
            except Exception:
                # If cannot unlink, replace will overwrite below
                pass
            try:
                shutil.move(str(path), str(bak))
            except Exception:
                # If moving fails (e.g., permission), try copying then unlink
                try:
                    shutil.copy2(str(path), str(bak))
                except Exception:
                    # Last resort, ignore backup failure
                    pass
        # Replace with tmp
        shutil.move(str(tmp), str(path))
        # Ensure data is on disk
        with path.open("r", encoding="utf-8") as f:
            os.fsync(f.fileno())
        if not bak.exists():
            try:
                shutil.copy2(str(path), str(bak))
            except Exception:
                pass
