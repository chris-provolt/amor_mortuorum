from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from .base import Scene
from ..state.run_state import RunState

logger = logging.getLogger(__name__)


@dataclass
class CombatContext:
    """Minimal combat context placeholder.

    In a full implementation this would include enemies, turn order, etc.
    """
    floor: int
    start_position: Tuple[int, int]


class CombatScene(Scene):
    name = "combat"

    def __init__(self, run_state: RunState, start_position: Tuple[int, int]):
        self.run_state = run_state
        self.context = CombatContext(floor=run_state.floor, start_position=start_position)

    def on_enter(self, previous: Optional[Scene]) -> None:
        logger.info(
            "Entering Combat: floor=%s at pos=%s", self.context.floor, self.context.start_position
        )
