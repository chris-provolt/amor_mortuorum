from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import os
import pickle
import random
from pathlib import Path
from typing import Optional, Tuple

from platformdirs import PlatformDirs

from .. import __version__
from ..models.run_state import RunState
from ..utils.crypto import HMACKeyManager, hmac_sign, hmac_verify
from ..utils.fs import ensure_dir, atomic_write_json
from ..utils.jsonutil import canonical_dumps

logger = logging.getLogger(__name__)


class SnapshotError(Exception):
    pass


class SnapshotIntegrityError(SnapshotError):
    pass


class SnapshotDecodeError(SnapshotError):
    pass


class SnapshotManager:
    """Manages a single volatile run snapshot for save-and-quit.

    Design goals:
    - Single slot only (prevents scumming via multiple states)
    - Snapshot is consumed on successful load
    - Atomic writes to avoid corruption
    - HMAC over canonical payload to discourage tampering

    Snapshot file schema (JSON):
    {
      "schema_version": 1,
      "slot_id": 1,
      "created_at": ISO8601,
      "game_version": str,
      "run_state": {...},  # RunState JSON
      "rng_state": str,    # base64-encoded pickle of random.Random state
      "hmac": str          # hex digest over canonical payload (excludes hmac field)
    }
    """

    SCHEMA_VERSION = 1

    def __init__(self, *, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            d = PlatformDirs(appname="AmorMortuorum", appauthor="AmorMortuorumTeam")
            base_dir = Path(d.user_data_dir)
        self.base_dir = base_dir
        self.save_dir = self.base_dir / "saves"
        self.snapshot_path = self.save_dir / "snapshot.json"
        self.key_mgr = HMACKeyManager(base_dir=self.base_dir)
        ensure_dir(self.save_dir)

    def has_snapshot(self) -> bool:
        return self.snapshot_path.exists()

    def clear_snapshot(self) -> None:
        try:
            if self.snapshot_path.exists():
                self.snapshot_path.unlink()
        except Exception:
            logger.warning("Failed to remove snapshot file", exc_info=True)

    def _encode_rng_state(self, rng: random.Random) -> str:
        s = rng.getstate()
        b = pickle.dumps(s, protocol=pickle.HIGHEST_PROTOCOL)
        return base64.b64encode(b).decode("ascii")

    def _decode_rng_state(self, enc: str) -> random.Random:
        try:
            b = base64.b64decode(enc.encode("ascii"))
            s = pickle.loads(b)
            rng = random.Random()
            rng.setstate(s)
            return rng
        except Exception as e:
            raise SnapshotDecodeError("Failed to decode RNG state") from e

    def save_snapshot(self, run_state: RunState, rng: random.Random) -> None:
        """Persist the current run state and PRNG state atomically.

        Intended to be called on explicit save-and-quit.
        """
        run_state.validate()
        key = self.key_mgr.get_or_create_key()
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "slot_id": 1,
            "created_at": dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat(),
            "game_version": __version__,
            "run_state": run_state.to_dict(),
            "rng_state": self._encode_rng_state(rng),
        }
        payload_bytes = canonical_dumps(payload).encode("utf-8")
        digest_hex = hmac_sign(payload_bytes, key)
        snapshot = dict(payload)
        snapshot["hmac"] = digest_hex
        atomic_write_json(self.snapshot_path, snapshot)
        logger.info("Saved volatile snapshot to %s", self.snapshot_path)

    def _read_snapshot(self) -> dict:
        try:
            raw = self.snapshot_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data
        except Exception as e:
            raise SnapshotDecodeError("Failed to read snapshot file") from e

    def _verify_snapshot(self, data: dict) -> None:
        key = self.key_mgr.get_or_create_key()
        if data.get("schema_version") != self.SCHEMA_VERSION:
            raise SnapshotIntegrityError("Unsupported snapshot schema version")
        if data.get("slot_id") != 1:
            raise SnapshotIntegrityError("Invalid snapshot slot id")
        digest_hex = data.get("hmac")
        if not isinstance(digest_hex, str):
            raise SnapshotIntegrityError("Missing snapshot HMAC")
        payload = {k: v for k, v in data.items() if k != "hmac"}
        if not hmac_verify(canonical_dumps(payload).encode("utf-8"), key, digest_hex):
            raise SnapshotIntegrityError("Snapshot HMAC verification failed")

    def load_snapshot(self) -> Tuple[RunState, random.Random]:
        """Load and consume the volatile snapshot.

        Returns the RunState and RNG ready to continue the run.
        On integrity failure or decode error, the snapshot is cleared and an exception raised.
        """
        if not self.snapshot_path.exists():
            raise SnapshotError("No snapshot found")

        data = self._read_snapshot()
        try:
            self._verify_snapshot(data)
            run_state = RunState.from_dict(data["run_state"])
            rng = self._decode_rng_state(data["rng_state"])
        except Exception:
            # On any issue, clear snapshot to prevent repeated attempts and scumming
            self.clear_snapshot()
            raise

        # Consume snapshot after successfully reconstructing state
        try:
            os.remove(self.snapshot_path)
        except Exception:
            logger.warning("Failed to delete snapshot after load", exc_info=True)

        logger.info("Loaded and consumed volatile snapshot from %s", self.snapshot_path)
        return run_state, rng

    def get_snapshot_metadata(self) -> Optional[dict]:
        if not self.has_snapshot():
            return None
        try:
            data = self._read_snapshot()
            # Do not verify HMAC here to allow UI to show presence even if invalid; but keep minimal metadata
            return {
                "schema_version": data.get("schema_version"),
                "slot_id": data.get("slot_id"),
                "created_at": data.get("created_at"),
                "game_version": data.get("game_version"),
            }
        except Exception:
            return None
