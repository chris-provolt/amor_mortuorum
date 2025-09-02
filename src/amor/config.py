from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """
    Central application configuration.

    Values may be overridden via environment variables at runtime.
    This module is independent from any rendering/game framework and is safe to import in tests.
    """

    app_name: str = "Amor Mortuorum"
    build_version: str = os.getenv("AMOR_BUILD_VERSION", "dev")

    # Debug & overlay
    debug_enabled: bool = field(default_factory=lambda: os.getenv("AMOR_DEBUG", "0") == "1")
    debug_overlay: bool = field(default_factory=lambda: os.getenv("AMOR_DEBUG_OVERLAY", "0") == "1")

    # Telemetry
    telemetry_enabled: bool = field(default_factory=lambda: os.getenv("AMOR_TELEMETRY", "1") == "1")
    telemetry_dir: Path = field(default_factory=lambda: Path(os.getenv("AMOR_TELEMETRY_DIR", str(Path.home() / ".amor" / "telemetry"))))
    telemetry_flush_size: int = int(os.getenv("AMOR_TELEMETRY_FLUSH_SIZE", "50"))

    # Determinism / RNG seed
    seed: Optional[int] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        cfg = cls()
        seed_env = os.getenv("AMOR_SEED")
        if seed_env:
            try:
                cfg.seed = int(seed_env)
            except ValueError:
                # allow hex or arbitrary strings via hashing in SeedManager. Here we store as None and let manager derive.
                cfg.seed = None
        return cfg

    def ensure_dirs(self) -> None:
        if self.telemetry_enabled:
            self.telemetry_dir.mkdir(parents=True, exist_ok=True)
