from __future__ import annotations

import logging
from typing import Callable

from ..config import GameConfig
from ..events import MovementEvent
from ..scenes.combat import CombatScene
from ..scenes.manager import SceneManager
from ..state.run_state import RunState

logger = logging.getLogger(__name__)


class EncounterSystem:
    """Handles random encounter checks on tile movement."""

    def __init__(self, config: GameConfig, scene_provider: Callable[[], object], run_state: RunState) -> None:
        self.config = config
        self._scene_provider = scene_provider
        self.run_state = run_state

    @property
    def scene_manager(self) -> SceneManager:
        # Late import to avoid circulars for tests that construct a SceneManager externally.
        from ..scenes.manager import SceneManager as _SM

        scene_provider_obj = self._scene_provider()
        # We expect the provider object (scene) to have an attribute set by the integrator
        # or a global manager. For this self-contained module, we'll attach it manually in tests.
        manager = getattr(scene_provider_obj, "scene_manager", None)
        if not isinstance(manager, _SM):
            raise RuntimeError(
                "EncounterSystem requires the hosting scene to expose a SceneManager via 'scene_manager'"
            )
        return manager

    def on_tile_entered(self, event: MovementEvent) -> None:
        """Perform encounter roll and transition to combat if triggered."""
        floor = self.run_state.floor
        rate = self.config.get_encounter_rate_for_floor(floor)
        roll = self.run_state.rng.random()
        logger.debug(
            "Encounter roll: roll=%.5f vs rate=%.5f (floor=%s)", roll, rate, floor
        )
        if roll < rate:
            logger.info("Encounter triggered at floor %s, position=%s", floor, event.position)
            combat = CombatScene(run_state=self.run_state, start_position=event.position)
            self.scene_manager.transition_to(combat)
        else:
            logger.debug("No encounter at this step.")
