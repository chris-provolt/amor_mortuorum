from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional, Set

from game.config.loader import MinibossConfig, load_miniboss_config
from game.events.bus import EventBus
from game.world.structures import Floor

logger = logging.getLogger(__name__)

# Event names used by the gate manager.
EVT_FLOOR_GENERATED = "floor.generated"  # payload: floor: Floor
EVT_MINIBOSS_DEFEATED = "combat.miniboss_defeated"  # payload: floor_depth: int
EVT_STAIRS_LOCK_CHANGED = "floor.stairs_lock_changed"  # payload: floor_depth: int, locked: bool, reason: str


@dataclass
class MinibossGateManager:
    """Controls miniboss gate logic across floors.

    Responsibilities:
    - On floor generation for 20/40/60/80, lock the stairs and ensure a miniboss room exists.
    - When the miniboss on that floor is defeated, unlock the stairs.

    Integration:
    - Subscribe to the shared EventBus to react to floor generation and combat outcomes.
    - Emits EVT_STAIRS_LOCK_CHANGED whenever it mutates stairs lock state.
    """

    bus: EventBus
    config: MinibossConfig

    def __init__(self, bus: EventBus, config: Optional[MinibossConfig] = None) -> None:
        self.bus = bus
        self.config = config or load_miniboss_config()
        self._gated_floors: Set[int] = set(self.config.floors)
        self._active_gated_floor: Optional[int] = None

        # Subscribe to required events
        self.bus.subscribe(EVT_FLOOR_GENERATED, self._on_floor_generated)
        self.bus.subscribe(EVT_MINIBOSS_DEFEATED, self._on_miniboss_defeated)
        logger.info("MinibossGateManager active. Gated floors: %s", sorted(self._gated_floors))

    # Public API (optional use)
    def is_gated_floor(self, depth: int) -> bool:
        return depth in self._gated_floors

    # Event handlers
    def _on_floor_generated(self, floor: Floor, **_: object) -> None:
        depth = floor.depth
        logger.debug("Handling floor.generated for depth=%s", depth)
        self._active_gated_floor = None

        if not self.is_gated_floor(depth):
            logger.debug("Depth %s is not a miniboss gate floor. No action taken.", depth)
            return

        lock_reason = self.config.lock_reason
        # Lock the stairs until miniboss is defeated.
        floor.stairs.lock(lock_reason)

        # Ensure a miniboss room exists; if not, create a placeholder.
        miniboss_room = floor.get_first_room_by_kind("miniboss")
        if miniboss_room is None:
            miniboss_room = floor.add_room("miniboss", name=f"Miniboss L{depth}")
            logger.info("Created miniboss room for depth %s: room_id=%s", depth, miniboss_room.id)
        else:
            logger.info("Miniboss room already present on depth %s: room_id=%s", depth, miniboss_room.id)

        floor.set_flag("miniboss_required", True)
        self._active_gated_floor = depth

        # Notify others about stairs lock change
        self.bus.emit(
            EVT_STAIRS_LOCK_CHANGED, floor_depth=depth, locked=True, reason=lock_reason
        )

    def _on_miniboss_defeated(self, floor_depth: int, **_: object) -> None:
        logger.debug("Handling combat.miniboss_defeated for floor_depth=%s", floor_depth)
        if not self.is_gated_floor(floor_depth):
            logger.debug("Miniboss defeat reported for non-gated floor %s; ignoring.", floor_depth)
            return

        if self._active_gated_floor is not None and self._active_gated_floor != floor_depth:
            # This can happen if multiple floors are kept alive; we still handle unlock.
            logger.debug(
                "Active gated floor %s differs from defeat floor %s; proceeding anyway.",
                self._active_gated_floor,
                floor_depth,
            )

        # We need a way to get the floor object to unlock its stairs. In an integrated
        # engine this would come from a FloorManager or WorldState. For this module,
        # we broadcast a request-response pattern so the host can return the floor.
        floors: Iterable[Floor] = self._request_floors_for_depth(floor_depth)
        unlocked_any = False
        for fl in floors:
            if fl.depth != floor_depth:
                continue
            previously_locked = fl.stairs.locked
            fl.stairs.unlock_reason(self.config.lock_reason)
            if previously_locked and not fl.stairs.locked:
                unlocked_any = True
                fl.set_flag("miniboss_required", False)
                logger.info("Unlocked stairs for depth %s after miniboss defeat", floor_depth)
                self.bus.emit(
                    EVT_STAIRS_LOCK_CHANGED,
                    floor_depth=floor_depth,
                    locked=False,
                    reason=self.config.lock_reason,
                )
        if not unlocked_any:
            logger.debug(
                "No stairs unlocked for floor %s (maybe already unlocked or floor not found)",
                floor_depth,
            )

    # Request floors by broadcasting a query and collecting any responses.
    # Hosts can subscribe to EVT_QUERY_FLOORS to return Floor instances.
    EVT_QUERY_FLOORS = "world.query_floors"  # payload: depth:int -> return List[Floor]

    def _request_floors_for_depth(self, depth: int) -> Iterable[Floor]:
        try:
            results = self.bus.emit(self.EVT_QUERY_FLOORS, depth=depth)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Error querying floors for depth %s", depth)
            results = []
        for res in results:
            if res is None:
                continue
            if isinstance(res, list):
                for item in res:
                    if isinstance(item, Floor):
                        yield item
            elif isinstance(res, Floor):
                yield res
            else:
                logger.debug("Ignoring non-Floor result from query: %r", res)
