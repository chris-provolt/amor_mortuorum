from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from platformdirs import user_data_dir
except Exception:  # pragma: no cover
    def user_data_dir(appname: str, appauthor: Optional[str] = None) -> str:
        return str(Path.home() / f".{appname}")

log = logging.getLogger(__name__)


class SaveManager:
    """Manage save snapshots for Continue functionality.

    For now, we support a single continue snapshot that represents the latest
    run-in-progress. In the future, this can be extended to multiple save slots.
    """

    def __init__(self, app_name: str = "AmorMortuorum", data_dir: Optional[Path] = None) -> None:
        self.app_name = app_name
        self.data_dir = Path(data_dir) if data_dir else Path(user_data_dir(appname=app_name))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file = self.data_dir / "continue_snapshot.json"

    def has_snapshot(self) -> bool:
        return self.snapshot_file.exists()

    def create_snapshot(self, data: Dict[str, Any]) -> None:
        """Create or overwrite the continue snapshot with provided data.

        Args:
            data: Any JSON-serializable data representing the game state.
        """
        try:
            self.snapshot_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            log.info("Continue snapshot saved to %s", self.snapshot_file)
        except Exception:
            log.exception("Failed to create snapshot")
            raise

    def load_snapshot(self) -> Dict[str, Any]:
        """Load the continue snapshot.

        Returns:
            The JSON-decoded snapshot data.
        Raises:
            FileNotFoundError if no snapshot exists.
            ValueError if the contents are invalid.
        """
        if not self.snapshot_file.exists():
            raise FileNotFoundError("No continue snapshot found")
        try:
            return json.loads(self.snapshot_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.exception("Invalid snapshot JSON")
            raise ValueError("Invalid snapshot JSON") from e

    def delete_snapshot(self) -> None:
        try:
            if self.snapshot_file.exists():
                self.snapshot_file.unlink()
                log.info("Continue snapshot deleted")
        except Exception:
            log.exception("Failed to delete snapshot")
            raise
