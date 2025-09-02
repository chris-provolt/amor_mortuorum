from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from ..rng import RNGManager

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


@dataclass(frozen=True)
class ChestContent:
    position: Point
    item_id: str


class ChestGenerator:
    """Deterministic chest loot generator.

    Loot is determined per-chest using a RNG derived from (master_seed, floor, x, y)
    so that results do not depend on iteration order and are fully reproducible.
    """

    def __init__(self, rngm: RNGManager) -> None:
        self.rngm = rngm

        # Simple item tables by tier; in a real game these would be data-driven.
        self.tiers: Dict[str, List[str]] = {
            "common": [
                "potion",
                "antidote",
                "torch",
                "bandage",
            ],
            "uncommon": [
                "iron_sword",
                "leather_armor",
                "stamina_tonic",
                "smoke_bomb",
            ],
            "rare": [
                "magic_scroll",
                "ruby_ring",
                "obsidian_dagger",
                "elixir",
            ],
        }

    def _tier_weights(self, floor: int) -> Tuple[int, int, int]:
        """Return weights (common, uncommon, rare) adjusted by floor depth.

        Starts at 70/25/5 and gradually shifts towards higher tiers with depth.
        """
        rare = min(30, 5 + floor // 5)  # up to 30
        uncommon = min(50, 25 + floor // 3)  # up to 50
        common = max(20, 100 - (rare + uncommon))  # ensure at least some common
        # Normalize to sum to 100
        total = common + uncommon + rare
        k = 100 / total
        common = int(round(common * k))
        uncommon = int(round(uncommon * k))
        rare = 100 - common - uncommon
        return (common, uncommon, rare)

    def _weighted_choice(self, rng, items: List[str], weights: List[int]) -> str:
        assert len(items) == len(weights)
        total = sum(weights)
        r = rng.randint(1, total)
        upto = 0
        for item, w in zip(items, weights):
            upto += w
            if r <= upto:
                return item
        # Fallback (should not occur)
        return items[-1]

    def generate_for_positions(self, floor: int, chests: Iterable[Point]) -> List[ChestContent]:
        contents: List[ChestContent] = []
        common_w, uncommon_w, rare_w = self._tier_weights(floor)
        for (x, y) in chests:
            rng = self.rngm.context_rng("chest_loot", floor, x, y)
            # First choose tier
            tier = self._weighted_choice(
                rng,
                ["common", "uncommon", "rare"],
                [common_w, uncommon_w, rare_w],
            )
            # Then choose specific item from tier uniformly
            items = self.tiers[tier]
            idx = rng.randrange(0, len(items))
            contents.append(ChestContent(position=(x, y), item_id=items[idx]))
        # Deterministic order (sort by position)
        return sorted(contents, key=lambda c: (c.position[1], c.position[0]))
