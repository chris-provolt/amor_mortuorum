import logging
from typing import Optional

from amor.game.events import BossDefeatedEvent
from amor.meta.relics import RelicManager

logger = logging.getLogger(__name__)


class BossDefeatService:
    """Handles post-boss-defeat logic, including final relic award.

    This service's on_boss_defeated method should be called by the combat
    resolution flow when a boss is defeated. It will ensure the final relic is
    awarded exactly once upon a valid final boss (B99) kill and persisted.
    """

    def __init__(self, relics: RelicManager) -> None:
        self._relics = relics

    def on_boss_defeated(self, event: BossDefeatedEvent) -> bool:
        """Process boss defeat. Returns True if a new relic was awarded.

        Criteria for final relic (Heart of Oblivion):
          - event.is_final is True (combat system determines correctness)
          - event.floor == 99 (defensive check)

        The relic is only awarded once, and persisted via RelicManager.
        """
        if event.is_final and event.floor == 99:
            logger.info("Final boss defeated on run %s by boss '%s'. Checking relic award...", event.run_id, event.boss_id)
            awarded = self._relics.award_final_relic()
            if awarded:
                logger.info("Final relic awarded and persisted.")
            else:
                logger.info("Final relic was already collected; no award.")
            return awarded
        else:
            logger.debug(
                "Boss defeated not eligible for final relic (floor=%s, is_final=%s, boss_id=%s)",
                event.floor,
                event.is_final,
                event.boss_id,
            )
            return False
