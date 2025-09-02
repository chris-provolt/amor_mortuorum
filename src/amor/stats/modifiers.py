from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class GlobalModifiers:
    """Global modifiers that apply game-wide.

    This is the aggregation target for all enabled Relic passives and any other global effects.

    - stat_multipliers: Multiplicative factors for core stats (1.0 means no change).
    - gold_find_multiplier: Multiplier applied to gold rewards.
    - item_find_multiplier: Multiplier applied to item drop chances.
    - portal_chance_delta: Flat delta added to the portal spawn chance (in 0..1 domain).
    - light_radius_delta: Integer delta for FOV/vision radius.
    - trap_detect_chance_delta: Flat delta added to trap detection chance (in 0..1 domain).
    """

    stat_multipliers: Dict[str, float] = field(
        default_factory=lambda: {"HP": 1.0, "ATK": 1.0, "DEF": 1.0, "SPD": 1.0}
    )
    gold_find_multiplier: float = 1.0
    item_find_multiplier: float = 1.0
    portal_chance_delta: float = 0.0
    light_radius_delta: int = 0
    trap_detect_chance_delta: float = 0.0

    def combine(self, other: GlobalModifiers) -> GlobalModifiers:
        """Combine two GlobalModifiers into one, multiplying multipliers and adding deltas.

        Args:
            other: Another GlobalModifiers instance.
        Returns:
            A new GlobalModifiers representing the combination of self and other.
        """
        sm: Dict[str, float] = {}
        keys = set(self.stat_multipliers.keys()) | set(other.stat_multipliers.keys())
        for k in keys:
            sm[k] = self.stat_multipliers.get(k, 1.0) * other.stat_multipliers.get(k, 1.0)

        combined = GlobalModifiers(
            stat_multipliers=sm,
            gold_find_multiplier=self.gold_find_multiplier * other.gold_find_multiplier,
            item_find_multiplier=self.item_find_multiplier * other.item_find_multiplier,
            portal_chance_delta=self.portal_chance_delta + other.portal_chance_delta,
            light_radius_delta=self.light_radius_delta + other.light_radius_delta,
            trap_detect_chance_delta=self.trap_detect_chance_delta + other.trap_detect_chance_delta,
        )
        logger.debug("Combined GlobalModifiers => %s", combined)
        return combined

    def to_dict(self) -> Dict:
        return {
            "stat_multipliers": dict(self.stat_multipliers),
            "gold_find_multiplier": self.gold_find_multiplier,
            "item_find_multiplier": self.item_find_multiplier,
            "portal_chance_delta": self.portal_chance_delta,
            "light_radius_delta": self.light_radius_delta,
            "trap_detect_chance_delta": self.trap_detect_chance_delta,
        }

    @staticmethod
    def from_dict(data: Dict) -> GlobalModifiers:
        return GlobalModifiers(
            stat_multipliers=dict(data.get("stat_multipliers", {})) or {"HP": 1.0, "ATK": 1.0, "DEF": 1.0, "SPD": 1.0},
            gold_find_multiplier=float(data.get("gold_find_multiplier", 1.0)),
            item_find_multiplier=float(data.get("item_find_multiplier", 1.0)),
            portal_chance_delta=float(data.get("portal_chance_delta", 0.0)),
            light_radius_delta=int(data.get("light_radius_delta", 0)),
            trap_detect_chance_delta=float(data.get("trap_detect_chance_delta", 0.0)),
        )


class StatsCalculator:
    """Utility for applying GlobalModifiers to a set of base stats.

    Base and resulting stats are plain dictionaries: {"HP": int, "ATK": int, ...}
    """

    @staticmethod
    def apply_modifiers(base_stats: Dict[str, float], mods: GlobalModifiers) -> Dict[str, float]:
        if not isinstance(mods, GlobalModifiers):
            raise TypeError("mods must be GlobalModifiers")
        result: Dict[str, float] = {}
        for k, v in base_stats.items():
            mult = mods.stat_multipliers.get(k, 1.0)
            result[k] = float(v) * float(mult)
        logger.debug("Applied modifiers %s to base %s => %s", mods, base_stats, result)
        return result
