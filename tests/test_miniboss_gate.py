import logging
from typing import List

import pytest

from game.config.loader import MinibossConfig
from game.encounters.miniboss_gate import (
    EVT_FLOOR_GENERATED,
    EVT_MINIBOSS_DEFEATED,
    EVT_STAIRS_LOCK_CHANGED,
    MinibossGateManager,
)
from game.events.bus import EventBus
from game.world.structures import Floor


@pytest.fixture(autouse=True)
def _configure_logging():
    logging.basicConfig(level=logging.DEBUG)


@pytest.fixture()
def bus() -> EventBus:
    return EventBus()


@pytest.fixture()
def config() -> MinibossConfig:
    # Use specific test config to avoid relying on resource file
    return MinibossConfig(floors=[20, 40, 60, 80], lock_reason="miniboss_gate")


@pytest.fixture()
def manager(bus: EventBus, config: MinibossConfig) -> MinibossGateManager:
    return MinibossGateManager(bus=bus, config=config)


def test_stairs_locked_on_miniboss_floor(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=20)

    lock_events = []
    bus.subscribe(
        EVT_STAIRS_LOCK_CHANGED,
        lambda floor_depth, locked, reason: lock_events.append((floor_depth, locked, reason)),
    )

    # Provide a handler to return floors when queried
    bus.subscribe(
        manager.EVT_QUERY_FLOORS,
        lambda depth: [floor] if depth == floor.depth else [],
    )

    bus.emit(EVT_FLOOR_GENERATED, floor=floor)

    assert floor.get_flag("miniboss_required") is True
    assert floor.stairs.locked is True
    assert (20, True, "miniboss_gate") in lock_events


def test_stairs_unlocked_after_miniboss_defeat(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=20)

    # Provide query to resolve Floor from depth
    bus.subscribe(manager.EVT_QUERY_FLOORS, lambda depth: [floor])

    # Generate floor (locks stairs)
    bus.emit(EVT_FLOOR_GENERATED, floor=floor)
    assert floor.stairs.locked is True

    unlock_events = []
    bus.subscribe(
        EVT_STAIRS_LOCK_CHANGED,
        lambda floor_depth, locked, reason: unlock_events.append((floor_depth, locked, reason)),
    )

    # Defeat miniboss and ensure stairs unlock
    bus.emit(EVT_MINIBOSS_DEFEATED, floor_depth=20)

    assert floor.stairs.locked is False
    assert floor.get_flag("miniboss_required") is False
    assert (20, False, "miniboss_gate") in unlock_events


def test_non_miniboss_floor_unchanged(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=21)
    bus.emit(EVT_FLOOR_GENERATED, floor=floor)
    assert floor.get_flag("miniboss_required") is None
    assert floor.stairs.locked is False


def test_idempotent_unlock(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=40)

    # Provide query to resolve Floor from depth
    bus.subscribe(manager.EVT_QUERY_FLOORS, lambda depth: [floor])

    bus.emit(EVT_FLOOR_GENERATED, floor=floor)
    assert floor.stairs.locked is True

    # Multiple defeat events should not error and should result in unlocked stairs
    bus.emit(EVT_MINIBOSS_DEFEATED, floor_depth=40)
    assert floor.stairs.locked is False

    bus.emit(EVT_MINIBOSS_DEFEATED, floor_depth=40)  # no-op
    assert floor.stairs.locked is False


def test_miniboss_room_created_if_missing(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=60)
    assert floor.get_first_room_by_kind("miniboss") is None

    bus.emit(EVT_FLOOR_GENERATED, floor=floor)

    room = floor.get_first_room_by_kind("miniboss")
    assert room is not None
    assert room.kind == "miniboss"
    assert isinstance(room.id, int) and room.id >= 1


def test_lock_reason_is_isolated(bus: EventBus, manager: MinibossGateManager):
    floor = Floor(depth=80)
    bus.subscribe(manager.EVT_QUERY_FLOORS, lambda depth: [floor])

    # Another system locks the stairs for a different reason (e.g., cutscene)
    floor.stairs.lock("cutscene")

    # Generate gated floor; now two lock reasons should exist
    bus.emit(EVT_FLOOR_GENERATED, floor=floor)
    assert floor.stairs.locked is True
    assert floor.stairs.lock_reasons == {"cutscene", "miniboss_gate"}

    # Miniboss defeat should remove only miniboss lock reason
    bus.emit(EVT_MINIBOSS_DEFEATED, floor_depth=80)
    assert floor.stairs.locked is True  # still locked due to cutscene
    assert floor.stairs.lock_reasons == {"cutscene"}
