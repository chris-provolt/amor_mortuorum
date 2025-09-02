import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class EconomyConfig:
    """Configuration knobs for gold economy.

    Defaults are sensible if external config is not present.
    """

    depth_gold_scale_base: float = 1.0
    depth_gold_scale_per_floor: float = 0.02  # +2% per floor
    chest_quality_multipliers: Dict[str, float] = field(
        default_factory=lambda: {
            "poor": 0.5,
            "normal": 1.0,
            "rich": 1.75,
            "rare": 2.5,
        }
    )
    base_chest_gold: int = 10
    chest_gold_per_floor: int = 2
    shop_price_modifier: float = 1.0


def load_economy_config(path: Path) -> EconomyConfig:
    if not path.exists():
        logger.warning("Economy config not found at %s; using defaults", path)
        return EconomyConfig()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.exception("Failed to load economy config: %s", e)
        return EconomyConfig()

    cfg = EconomyConfig()
    cfg.depth_gold_scale_base = float(data.get("depth_gold_scale_base", cfg.depth_gold_scale_base))
    cfg.depth_gold_scale_per_floor = float(data.get("depth_gold_scale_per_floor", cfg.depth_gold_scale_per_floor))
    cfg.base_chest_gold = int(data.get("base_chest_gold", cfg.base_chest_gold))
    cfg.chest_gold_per_floor = int(data.get("chest_gold_per_floor", cfg.chest_gold_per_floor))
    cfg.shop_price_modifier = float(data.get("shop_price_modifier", cfg.shop_price_modifier))
    q = data.get("chest_quality_multipliers", None)
    if isinstance(q, dict):
        cfg.chest_quality_multipliers = {str(k): float(v) for k, v in q.items()}
    return cfg
