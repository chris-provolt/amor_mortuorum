import logging
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional

from .config import EconomyConfig
from .wallet import GoldWallet

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Enemy:
    """Lightweight enemy descriptor for reward calculations.

    gold_value: expected base gold the enemy is worth at depth 0.
    name: optional identifier for debugging.
    """

    gold_value: int
    name: str = "enemy"


class CombatRewardCalculator:
    """Calculates gold rewards for combat outcomes given enemies and depth."""

    def __init__(self, config: Optional[EconomyConfig] = None) -> None:
        self.config = config or EconomyConfig()

    def compute_gold_for_enemies(self, enemies: Iterable[Enemy], depth: int) -> int:
        depth = max(0, depth)
        base_sum = sum(max(0, int(e.gold_value)) for e in enemies)
        scale = self.config.depth_gold_scale_base + self.config.depth_gold_scale_per_floor * depth
        scaled = int(round(base_sum * max(0.0, scale)))
        logger.debug(
            "Combat gold computed: base_sum=%s scale=%.4f depth=%s => %s",
            base_sum,
            scale,
            depth,
            scaled,
        )
        return max(0, scaled)

    def award_combat_gold(self, wallet: GoldWallet, enemies: Iterable[Enemy], depth: int) -> int:
        gold = self.compute_gold_for_enemies(enemies, depth)
        wallet.add(gold, reason="combat")
        return gold


class ChestRewardCalculator:
    """Calculates gold for chests based on quality and depth."""

    def __init__(self, config: Optional[EconomyConfig] = None) -> None:
        self.config = config or EconomyConfig()

    def compute_gold_for_chest(self, quality: str, depth: int) -> int:
        depth = max(0, depth)
        base = self.config.base_chest_gold + self.config.chest_gold_per_floor * depth
        mult = float(self.config.chest_quality_multipliers.get(quality.lower(), 1.0))
        gold = int(round(base * mult))
        logger.debug(
            "Chest gold computed: base=%s mult=%.2f quality=%s depth=%s => %s",
            base,
            mult,
            quality,
            depth,
            gold,
        )
        return max(0, gold)

    def award_chest_gold(self, wallet: GoldWallet, quality: str, depth: int) -> int:
        gold = self.compute_gold_for_chest(quality, depth)
        wallet.add(gold, reason="chest")
        return gold
