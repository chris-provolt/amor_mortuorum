from __future__ import annotations

"""Game state and transitions relevant to resurrection behavior."""

import logging
from dataclasses import dataclass

from amormortuorum.config import GRAVEYARD_LOCATION_NAME, RESURRECTION_POLICY
from amormortuorum.core.events import EventBus
from amormortuorum.models.inventory import Inventory
from amormortuorum.models.item import ITEM_ID_RESURRECTION_TOKEN
from amormortuorum.models.player import Player

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Holds high-level game state and processes critical transitions.

    Attributes:
        current_location: A simple string representing the current scene/location.
        events: EventBus used to publish transitions (e.g. player_revived).
    """

    current_location: str
    events: EventBus

    def handle_player_death(self, player: Player) -> None:
        """Handle player death with Resurrection Token behavior.

        If the player holds at least one Resurrection Token, consume exactly one,
        revive the player, and set location to the Graveyard. Otherwise, player
        remains dead (hp stays 0) and no location change occurs.
        """
        token = player.inventory.find_first_by_id(ITEM_ID_RESURRECTION_TOKEN)
        if token is None:
            logger.info("Player %s died without Resurrection Token.", player.name)
            self.events.emit("player_died", {"player": player, "location": self.current_location})
            return

        # Consume a single token
        removed = player.inventory.remove(token)
        if not removed:
            # Should not happen, but guard for consistency
            logger.error(
                "Resurrection Token found but could not be removed from inventory. Death proceeds.")
            self.events.emit("player_died", {"player": player, "location": self.current_location})
            return

        # Revive at Graveyard according to policy
        revive_hp = RESURRECTION_POLICY.compute_revive_hp(player.max_hp)
        player.heal_to(revive_hp)
        self.current_location = GRAVEYARD_LOCATION_NAME

        logger.info(
            "Player %s resurrected at %s with %d HP. Token consumed.",
            player.name,
            self.current_location,
            player.hp,
        )
        self.events.emit(
            "player_revived",
            {
                "player": player,
                "location": self.current_location,
                "hp": player.hp,
                "consumed_item_id": ITEM_ID_RESURRECTION_TOKEN,
            },
        )
