from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GameSession:
    """
    Holds session-scoped state that should persist for the lifetime of a run/session
    (but not necessarily across process restarts). This includes UI toggles such as
    minimap visibility and the current dungeon floor.
    """

    start_floor: int = 1
    minimap_visible: bool = True

    # Using field(init=False) so we can validate at __post_init__
    floor: int = field(default=1, init=False)

    def __post_init__(self) -> None:
        if self.start_floor < 1:
            logger.warning("start_floor < 1 provided (%s). Clamping to 1.", self.start_floor)
            self.start_floor = 1
        self.floor = self.start_floor
        logger.debug("GameSession initialized: floor=%s, minimap_visible=%s", self.floor, self.minimap_visible)

    def set_floor(self, floor: int) -> int:
        """Set the current dungeon floor, clamped to [1, 99] as a sensible bound.

        Returns the effective floor after clamping for convenience.
        """
        old = self.floor
        self.floor = max(1, min(99, int(floor)))
        logger.info("Floor set: %s -> %s", old, self.floor)
        return self.floor

    def next_floor(self) -> int:
        """Advance to the next floor (capped to 99)."""
        return self.set_floor(self.floor + 1)

    def toggle_minimap(self) -> bool:
        """Toggle minimap visibility and return the new state."""
        self.minimap_visible = not self.minimap_visible
        logger.info("Minimap visibility toggled: %s", self.minimap_visible)
        return self.minimap_visible
