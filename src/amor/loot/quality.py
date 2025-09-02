from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Mapping

from amor.items.models import ItemQuality

logger = logging.getLogger(__name__)

# Tier ranges aligned loosely with dungeon progression and miniboss breakpoints
# T1: 1-19, T2: 20-39, T3: 40-59, T4: 60-79, T5: 80-99

def get_floor_tier(floor: int) -> int:
    """
    Map a floor number (1..99) to a loot tier (1..5).
    Values outside 1..99 are clamped.
    """
    f = max(1, min(99, int(floor)))
    if f <= 19:
        return 1
    if f <= 39:
        return 2
    if f <= 59:
        return 3
    if f <= 79:
        return 4
    return 5


DEFAULT_QUALITY_WEIGHTS: Dict[int, Dict[ItemQuality, float]] = {
    1: {  # Floors 1-19
        ItemQuality.COMMON: 80,
        ItemQuality.UNCOMMON: 18,
        ItemQuality.RARE: 2,
        ItemQuality.EPIC: 0,
        ItemQuality.LEGENDARY: 0,
    },
    2: {  # Floors 20-39
        ItemQuality.COMMON: 65,
        ItemQuality.UNCOMMON: 28,
        ItemQuality.RARE: 6,
        ItemQuality.EPIC: 1,
        ItemQuality.LEGENDARY: 0,
    },
    3: {  # Floors 40-59
        ItemQuality.COMMON: 50,
        ItemQuality.UNCOMMON: 35,
        ItemQuality.RARE: 12,
        ItemQuality.EPIC: 3,
        ItemQuality.LEGENDARY: 0,
    },
    4: {  # Floors 60-79
        ItemQuality.COMMON: 35,
        ItemQuality.UNCOMMON: 38,
        ItemQuality.RARE: 18,
        ItemQuality.EPIC: 8,
        ItemQuality.LEGENDARY: 1,
    },
    5: {  # Floors 80-99
        ItemQuality.COMMON: 25,
        ItemQuality.UNCOMMON: 35,
        ItemQuality.RARE: 25,
        ItemQuality.EPIC: 12,
        ItemQuality.LEGENDARY: 3,
    },
}


def _load_quality_weights_from_config() -> Dict[int, Dict[ItemQuality, float]] | None:
    """
    Optionally load tier-based quality weights from a JSON config.
    Schema:
    {
      "tiers": {
        "1": {"common": 80, "uncommon": 18, ...},
        ...
      }
    }
    """
    try:
        root = Path(__file__).resolve().parents[3]  # .../src/amor/loot/quality.py -> repo root
        cfg_dir = Path(os.environ.get("AMOR_CONFIG_DIR", root / "configs"))
        path = cfg_dir / "loot" / "quality_weights.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        result: Dict[int, Dict[ItemQuality, float]] = {}
        for tier_str, weights in data.get("tiers", {}).items():
            t = int(tier_str)
            mapped: Dict[ItemQuality, float] = {}
            for k, v in weights.items():
                mapped[ItemQuality(k)] = float(v)
            result[t] = mapped
        logger.info("Loaded quality weights from config at %s", path)
        return result
    except Exception as e:  # pragma: no cover - defensive path
        logger.exception("Failed to load quality weights config: %s", e)
        return None


def get_quality_weights_for_floor(floor: int) -> Dict[ItemQuality, float]:
    """
    Get the quality weight mapping for a given floor. If a config file is
    available, it is used; otherwise defaults are returned.
    """
    tier = get_floor_tier(floor)
    config = _load_quality_weights_from_config()
    if config and tier in config:
        return config[tier]
    return DEFAULT_QUALITY_WEIGHTS[tier]


__all__ = ["get_floor_tier", "get_quality_weights_for_floor", "DEFAULT_QUALITY_WEIGHTS"]
