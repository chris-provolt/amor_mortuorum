from __future__ import annotations

import hashlib
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

try:
    # platformdirs is the modern successor to appdirs
    from platformdirs import PlatformDirs
except Exception as exc:  # pragma: no cover - defensive import error path
    raise RuntimeError(
        "platformdirs is required for amormortuorum.io.paths. Add platformdirs to your dependencies."
    ) from exc


LOGGER = logging.getLogger("amormortuorum.io.paths")
LOGGER.addHandler(logging.NullHandler())

APP_NAME = "Amor Mortuorum"

# Environment variable overrides (useful for tests and power users)
ENV_CONFIG_DIR = "AMOR_CONFIG_DIR"
ENV_SAVE_DIR = "AMOR_SAVE_DIR"
ENV_LOG_DIR = "AMOR_LOG_DIR"
ENV_CACHE_DIR = "AMOR_CACHE_DIR"


@dataclass
class MigrationAction:
    category: str  # "config" or "saves" or other
    src: Optional[Path]
    dest: Path
    moved_files: list[Path]
    skipped_files: list[Path]
    renamed_files: list[tuple[Path, Path]]
    errors: list[str]


@dataclass
class MigrationResult:
    actions: list[MigrationAction]

    @property
    def migrated(self) -> bool:
        return any(a.moved_files or a.renamed_files for a in self.actions)


class AppPaths:
    """Resolve and manage platform-appropriate directories for the app.

    Provides:
    - config_dir: user configuration files (YAML/JSON settings, keybindings, etc.)
    - save_dir: user data files (save slots, persistent meta progression)
    - log_dir: user log files directory
    - cache_dir: derived or cached data

    Behavior:
    - Uses platformdirs for cross-platform correctness.
    - Supports environment variable overrides for testing and portability.
    - Migrates content from common scaffolding directories to the proper locations.
    """

    def __init__(self, app_name: str = APP_NAME) -> None:
        self._dirs = PlatformDirs(appname=app_name, appauthor=False)

        # Compute directories with overrides
        self._config_dir = self._compute_dir(ENV_CONFIG_DIR, Path(self._dirs.user_config_dir))
        # Saves are placed under the platform-specific user data dir in a "saves" subdirectory
        self._save_dir = self._compute_dir(ENV_SAVE_DIR, Path(self._dirs.user_data_dir) / "saves")
        # Logs
        # platformdirs provides user_log_dir in newer versions; if missing, fallback to data/logs
        default_log_dir = getattr(self._dirs, "user_log_dir", None) or (Path(self._dirs.user_data_dir) / "logs")
        self._log_dir = self._compute_dir(ENV_LOG_DIR, Path(default_log_dir))
        # Cache
        self._cache_dir = self._compute_dir(ENV_CACHE_DIR, Path(self._dirs.user_cache_dir))

    @staticmethod
    def _compute_dir(env_var: str, default: Path) -> Path:
        override = os.getenv(env_var)
        if override:
            return Path(override).expanduser().resolve()
        return Path(default).expanduser().resolve()

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    @property
    def save_dir(self) -> Path:
        return self._save_dir

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def ensure_dirs(self) -> None:
        """Create all app directories if they don't exist, with sensible permissions."""
        for d in (self.config_dir, self.save_dir, self.log_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._write_dir_readme(self.config_dir, "Configuration files for Amor Mortuorum.")
        self._write_dir_readme(self.save_dir, "Save files for Amor Mortuorum.")
        self._write_dir_readme(self.log_dir, "Log files for Amor Mortuorum.")
        self._write_dir_readme(self.cache_dir, "Cache for Amor Mortuorum (safe to delete).")

    def migrate_from_scaffold(self, scaffold_root: Optional[Path] = None) -> MigrationResult:
        """Migrate configs and saves from common repository scaffolding directories.

        This supports moving from a dev layout like:
        - ./configs -> config_dir
        - ./data/saves or ./saves -> save_dir

        Migration is conservative: existing destination files are preserved; files are only
        moved if they don't already exist. If a conflicting file exists, the source file is
        preserved with a .migrated timestamp suffix.
        """
        root = self._resolve_scaffold_root(scaffold_root)
        self.ensure_dirs()

        actions: list[MigrationAction] = []

        # Candidates (first match wins) relative to root
        config_candidates = [
            root / "configs",
            root / "config",
            root / "settings",
        ]
        save_candidates = [
            root / "data" / "saves",
            root / "saves",
            root / "savegames",
        ]

        actions.append(self._migrate_category("config", config_candidates, self.config_dir))
        actions.append(self._migrate_category("saves", save_candidates, self.save_dir))

        return MigrationResult(actions=actions)

    # --------------------- Internal helpers ---------------------

    def _resolve_scaffold_root(self, explicit: Optional[Path]) -> Path:
        if explicit:
            return Path(explicit).expanduser().resolve()
        # Prefer current working directory; fall back to the project root if run from package
        cwd = Path.cwd()
        if (cwd / "configs").exists() or (cwd / "data").exists():
            return cwd
        # Attempt to find a repo root relative to this file (two levels up from src package)
        pkg_root = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) >= 4 else Path(__file__).resolve().parent
        return pkg_root

    def _migrate_category(
        self, category: str, src_candidates: Iterable[Path], dest_dir: Path
    ) -> MigrationAction:
        chosen_src: Optional[Path] = None
        for c in src_candidates:
            if c.exists() and self._has_content(c):
                chosen_src = c
                break

        moved: list[Path] = []
        skipped: list[Path] = []
        renamed: list[tuple[Path, Path]] = []
        errors: list[str] = []

        if not chosen_src:
            # Nothing to migrate
            return MigrationAction(category, None, dest_dir, moved, skipped, renamed, errors)

        LOGGER.info("Migrating %s from '%s' -> '%s'", category, chosen_src, dest_dir)
        # Merge/move contents into dest
        try:
            for src_child in sorted(chosen_src.iterdir()):
                try:
                    result = self._move_or_merge(src_child, dest_dir / src_child.name)
                    moved.extend(result["moved"])  # type: ignore[index]
                    skipped.extend(result["skipped"])  # type: ignore[index]
                    renamed.extend(result["renamed"])  # type: ignore[index]
                except Exception as move_exc:  # pragma: no cover - defensive path
                    msg = f"Failed to migrate '{src_child}': {move_exc}"
                    LOGGER.exception(msg)
                    errors.append(msg)
            # Clean up empty directories left behind
            self._prune_if_empty(chosen_src)
            # Write migration log into destination
            self._write_migration_log(dest_dir, chosen_src, moved, skipped, renamed, errors)
        except Exception as exc:  # pragma: no cover - defensive path
            msg = f"Migration for {category} failed: {exc}"
            LOGGER.exception(msg)
            errors.append(msg)

        return MigrationAction(category, chosen_src, dest_dir, moved, skipped, renamed, errors)

    @staticmethod
    def _has_content(p: Path) -> bool:
        if not p.exists():
            return False
        if p.is_file():
            return p.stat().st_size > 0
        # Directory: has any items
        return any(p.iterdir())

    def _move_or_merge(self, src: Path, dest: Path) -> dict[str, list]:
        """Move a file or directory from src into dest, merging if needed.

        - If dest doesn't exist, move src -> dest.
        - If dest exists:
          - For directories: recursively merge children.
          - For files: if identical, skip; otherwise, preserve destination and rename source with a .migrated timestamp.
        Returns dict of moved/skipped/renamed paths.
        """
        moved: list[Path] = []
        skipped: list[Path] = []
        renamed: list[tuple[Path, Path]] = []

        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved.append(dest)
            return {"moved": moved, "skipped": skipped, "renamed": renamed}

        # Both exist
        if src.is_dir() and dest.is_dir():
            # Merge every child recursively
            for child in sorted(src.iterdir()):
                child_result = self._move_or_merge(child, dest / child.name)
                moved.extend(child_result["moved"])  # type: ignore[index]
                skipped.extend(child_result["skipped"])  # type: ignore[index]
                renamed.extend(child_result["renamed"])  # type: ignore[index]
            # Remove empty directory
            self._prune_if_empty(src)
            return {"moved": moved, "skipped": skipped, "renamed": renamed}

        if src.is_file() and dest.is_file():
            if self._files_identical(src, dest):
                # Same content, drop source duplicate
                skipped.append(dest)
                try:
                    src.unlink(missing_ok=True)
                except Exception:  # pragma: no cover - defensive path
                    LOGGER.debug("Failed to unlink duplicate source file '%s'", src)
                return {"moved": moved, "skipped": skipped, "renamed": renamed}
            # Conflict: preserve destination, rename source with .migrated suffix
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            migrated_name = f"{src.name}.migrated.{ts}"
            migrated_path = src.with_name(migrated_name)
            src.rename(migrated_path)
            # Move the renamed file next to the destination for visibility
            final_migrated = dest.with_name(migrated_name)
            shutil.move(str(migrated_path), str(final_migrated))
            renamed.append((dest, final_migrated))
            return {"moved": moved, "skipped": skipped, "renamed": renamed}

        # One is file and the other is directory -> rename source and move
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        migrated_name = f"{src.name}.migrated.{ts}"
        migrated_src = src.with_name(migrated_name)
        src.rename(migrated_src)
        final_migrated = dest.with_name(migrated_name)
        shutil.move(str(migrated_src), str(final_migrated))
        renamed.append((dest, final_migrated))
        return {"moved": moved, "skipped": skipped, "renamed": renamed}

    @staticmethod
    def _files_identical(a: Path, b: Path) -> bool:
        try:
            if a.stat().st_size != b.stat().st_size:
                return False
        except FileNotFoundError:
            return False
        # Hash both (small files typical for configs/saves)
        return AppPaths._md5(a) == AppPaths._md5(b)

    @staticmethod
    def _md5(p: Path, chunk_size: int = 65536) -> str:
        h = hashlib.md5()
        with p.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _prune_if_empty(p: Path) -> None:
        try:
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
                # attempt to prune parent if looks like a scaffold dir
                if p.parent.name in {"data", "configs", "config"} and not any(p.parent.iterdir()):
                    p.parent.rmdir()
        except Exception:  # pragma: no cover - best-effort cleanup
            LOGGER.debug("Could not prune '%s' (may be non-empty or lacking permissions)", p)

    @staticmethod
    def _write_dir_readme(d: Path, description: str) -> None:
        readme = d / "README.txt"
        if readme.exists():
            return
        msg = (
            f"{description}\n\n"
            f"This directory was created by Amor Mortuorum to follow platform-appropriate\n"
            f"storage conventions using platformdirs.\n"
        )
        try:
            readme.write_text(msg, encoding="utf-8")
        except Exception:  # pragma: no cover - non-critical
            LOGGER.debug("Failed to write README to '%s'", readme)

    @staticmethod
    def _write_migration_log(dest_dir: Path, src_dir: Path, moved: list[Path], skipped: list[Path], renamed: list[tuple[Path, Path]], errors: list[str]) -> None:
        log_path = dest_dir / ".migration.log"
        lines = [
            f"[{datetime.utcnow().isoformat()}Z] Migration from '{src_dir}'\n",
            f"Moved: {len(moved)} files\n",
            f"Skipped (identical): {len(skipped)} files\n",
            f"Renamed (conflicts): {len(renamed)} files\n",
        ]
        if errors:
            lines.append(f"Errors: {len(errors)}\n")
            for e in errors:
                lines.append(f"- {e}\n")
        lines.append("\n")
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:  # pragma: no cover - non-critical
            LOGGER.debug("Failed to append migration log to '%s'", log_path)


def initialize_app_paths(scaffold_root: Optional[Path] = None) -> AppPaths:
    """Initialize and migrate directories. Call this early in application startup.

    Returns an AppPaths instance with platform-correct directories ensured and migrated.

    Environment overrides can be used to redirect directories (e.g., in tests):
    - AMOR_CONFIG_DIR
    - AMOR_SAVE_DIR
    - AMOR_LOG_DIR
    - AMOR_CACHE_DIR
    """
    paths = AppPaths()
    paths.ensure_dirs()
    result = paths.migrate_from_scaffold(scaffold_root)
    if result.migrated:
        LOGGER.info("Completed migration into platform directories.")
    return paths
