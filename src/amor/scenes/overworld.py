from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

from ..config import GameConfig
from ..events import MovementEvent
from ..state.run_state import RunState
from ..encounters.encounter_system import EncounterSystem
from .base import Scene

logger = logging.getLogger(__name__)


@dataclass
class Player:
    position: Tuple[int, int] = (0, 0)
    steps_taken: int = 0


class OverworldScene(Scene):
    """Represents the exploration scene on a floor or in the hub.

    This is where tile movements are processed, and encounter checks are made.
    """

    name = "overworld"

    def __init__(self, run_state: RunState, config: GameConfig, is_hub: bool = False) -> None:
        self.run_state = run_state
        self.config = config
        self.is_hub = is_hub
        self.player = Player()
        self.encounters = EncounterSystem(config=config, scene_provider=lambda: self, run_state=run_state)

    def on_enter(self, previous: Scene | None) -> None:
        logger.info(
            "Entered Overworld: floor=%s, hub=%s", self.run_state.floor, self.is_hub
        )

    def move_player(self, dx: int, dy: int) -> None:
        """Move player by delta and perform encounter check for the new tile."""
        x, y = self.player.position
        new_pos = (x + dx, y + dy)
        self.player.position = new_pos
        self.player.steps_taken += 1
        logger.debug(
            "Player moved to %s (steps=%s) on floor %s", new_pos, self.player.steps_taken, self.run_state.floor
        )
        event = MovementEvent(position=new_pos, steps_taken=self.player.steps_taken)
        if self.is_hub and not self.config.encounters_in_hub:
            logger.debug("Hub encounters disabled; skipping encounter check.")
            return
        # Otherwise, attempt encounter
        self.encounters.on_tile_entered(event)
