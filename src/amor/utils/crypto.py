from __future__ import annotations

import hmac
import logging
import os
from hashlib import sha256
from pathlib import Path
from typing import Optional

from platformdirs import PlatformDirs

from .fs import ensure_dir, atomic_write_bytes

logger = logging.getLogger(__name__)


class HMACKeyManager:
    """Manages a per-install HMAC key used to sign volatile snapshots.

    This discourages trivial tampering but is not intended as anti-cheat.
    """

    def __init__(self, *, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            d = PlatformDirs(appname="AmorMortuorum", appauthor="AmorMortuorumTeam")
            base_dir = Path(d.user_data_dir)
        self.base_dir = base_dir
        self.sec_dir = self.base_dir / "security"
        self.key_path = self.sec_dir / "snapshot_hmac.key"

    def get_or_create_key(self) -> bytes:
        if self.key_path.exists():
            try:
                return self.key_path.read_bytes()
            except Exception:
                logger.warning("Failed to read HMAC key; regenerating.", exc_info=True)
        # Generate new 32-byte key
        ensure_dir(self.sec_dir)
        key = os.urandom(32)
        atomic_write_bytes(self.key_path, key)
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            logger.debug("Could not chmod key file", exc_info=True)
        return key


def hmac_sign(payload_bytes: bytes, key: bytes) -> str:
    return hmac.new(key, payload_bytes, sha256).hexdigest()


def hmac_verify(payload_bytes: bytes, key: bytes, digest_hex: str) -> bool:
    expected = hmac_sign(payload_bytes, key)
    try:
        return hmac.compare_digest(expected, digest_hex)
    except Exception:
        return False
