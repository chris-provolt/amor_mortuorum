from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from amor.core.random import RandomSource
from amor.items.models import Item, ItemQuality
from amor.loot.loot_table import choose_item_by_quality
from amor.loot.quality import get_floor_tier, get_quality_weights_for_floor
from amor.player.player import Player

logger = logging.getLogger(__name__)


class ChestAlreadyOpenedError(RuntimeError):
    pass


@dataclass
class Chest:
    """
    A single-theme chest entity. When interacted with, it rolls an item quality based
    on the current floor's tier weights, chooses an item from that quality pool,
    adds the item to the player's inventory, and consumes the chest.
    """

    id: str = field(default_factory=lambda: "chest")
    consumed: bool = False

    def interact(
        self,
        player: Player,
        floor: int,
        rng: Optional[RandomSource] = None,
        quality_weights_override: Optional[Dict[ItemQuality, float]] = None,
    ) -> Item:
        """
        Open the chest, roll an item quality based on floor tier, grant the item, and consume chest.
        - Raises ChestAlreadyOpenedError if already consumed.
        - Returns the Item instance added to the inventory.
        """
        if self.consumed:
            logger.warning("Chest %s already opened", self.id)
            raise ChestAlreadyOpenedError("Chest has already been opened")

        if rng is None:
            rng = RandomSource()

        # Determine quality via tier-based weights
        if quality_weights_override is not None:
            weights = quality_weights_override
            logger.debug("Using override quality weights: %s", weights)
        else:
            weights = get_quality_weights_for_floor(floor)
            logger.debug(
                "Using tier-based quality weights for floor %s (tier %s): %s",
                floor,
                get_floor_tier(floor),
                weights,
            )

        quality: ItemQuality = rng.weighted_choice(weights)
        logger.info("Chest %s rolled item quality: %s", self.id, quality.value)

        # Select item from pool
        item = choose_item_by_quality(quality, rng=rng)
        logger.info("Chest %s chose item: %s (%s)", self.id, item.name, item.quality.value)

        # Add to inventory; if full, we can decide to drop on ground or raise.
        # For now, per acceptance criteria, ensure it appears in inventory; if it can't, raise.
        if not player.inventory.add(item):
            logger.error("Failed to add item %s to inventory: inventory full", item.id)
            raise RuntimeError("Inventory full; cannot add chest loot")

        # Consume chest
        self.consumed = True
        logger.debug("Chest %s consumed after loot", self.id)
        return item


__all__ = ["Chest", "ChestAlreadyOpenedError"]
