from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


CONFIG_PATHS = [
    Path("configs/combat.json"),
]


@dataclass
class CombatConfig:
    """
    Combat configuration with sensible defaults.

    You can override by providing configs/combat.json with keys:
      - defend_multiplier: float (default 0.5)
      - flee_min: float (default 0.2)
      - flee_max: float (default 0.95)
      - flee_base: float (default 0.5)
      - flee_scale: float (default 0.5)
      - flee_spd_aggregation: "average" or "sum" (default "average")
    """

    defend_multiplier: float = 0.5
    flee_min: float = 0.2
    flee_max: float = 0.95
    flee_base: float = 0.5
    flee_scale: float = 0.5
    flee_spd_aggregation: str = "average"

    @staticmethod
    def default() -> "CombatConfig":
        return CombatConfig()

    @staticmethod
    def load() -> "CombatConfig":
        data: Dict[str, Any] = {}
        for path in CONFIG_PATHS:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    logger.info("Loaded combat config from %s", path)
                    break
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning("Failed to load combat config from %s: %s", path, e)
                    data = {}
        cfg = CombatConfig(**{**CombatConfig.default().__dict__, **data})
        return cfg
