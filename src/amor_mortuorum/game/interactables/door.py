from __future__ import annotations

from dataclasses import dataclass
import logging

from ..interfaces import get_inventory_from, InventoryProtocol
from ..items import KEY_ITEM_ID

logger = logging.getLogger(__name__)


@dataclass
class DoorPassResult:
    """Result of attempting to pass a door.

    Attributes:
        allowed: Whether passage is allowed now (door open or opened now)
        consumed_key: Whether a key item was consumed to open the door
        was_open: Whether the door was already open prior to this attempt
        message: A user-facing message describing the outcome
    """

    allowed: bool
    consumed_key: bool
    was_open: bool
    message: str


class Door:
    """A door that blocks passage until opened with a key.

    Door is initially closed. Attempting to pass without a key blocks.
    Attempting to pass with a key consumes exactly one key and opens the door.

    Engine integration:
    - On movement into the door's tile, call `attempt_pass(actor)`.
    - If `result.allowed` is True, treat tile as passable (and keep door open).
    - Otherwise, block movement and optionally surface `result.message`.
    """

    def __init__(self, position: tuple[int, int], requires_key_id: str = KEY_ITEM_ID) -> None:
        self.position = position
        self.requires_key_id = requires_key_id
        self.is_open: bool = False

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        state = "open" if self.is_open else "closed"
        return f"<Door pos={self.position} state={state} requires={self.requires_key_id}>"

    def is_passable(self) -> bool:
        """Return True if the door is currently open (passable)."""
        return self.is_open

    def attempt_pass(self, actor: object) -> DoorPassResult:
        """Attempt to pass through the door with the given actor.

        If the door is already open, passage is allowed without consuming a key.
        If closed, the actor must have at least one key (by `requires_key_id`).
        On success, exactly one key is consumed and the door opens.
        On failure, passage is blocked and no items are consumed.
        """
        if self.is_open:
            logger.debug("Door at %s already open; allowing passage", self.position)
            return DoorPassResult(
                allowed=True,
                consumed_key=False,
                was_open=True,
                message="The door stands open.",
            )

        # Acquire an inventory adapter for the actor
        inv: InventoryProtocol = get_inventory_from(actor)

        count = inv.get_item_count(self.requires_key_id)
        logger.debug(
            "Attempting to pass closed door at %s; actor has %d '%s'",
            self.position,
            count,
            self.requires_key_id,
        )
        if count <= 0:
            logger.info(
                "Blocked by locked door at %s; no '%s' in inventory",
                self.position,
                self.requires_key_id,
            )
            return DoorPassResult(
                allowed=False,
                consumed_key=False,
                was_open=False,
                message="The door is locked. You need a key.",
            )

        # Consume one key and open the door
        try:
            inv.consume_item(self.requires_key_id, 1)
        except ValueError as e:  # Defensive: inventory reported count>0 but failed
            logger.exception("Failed to consume key for door at %s: %s", self.position, e)
            return DoorPassResult(
                allowed=False,
                consumed_key=False,
                was_open=False,
                message="The key slipped from your grasp. Try again.",
            )

        self.is_open = True
        logger.info(
            "Door at %s opened; consumed 1 '%s'", self.position, self.requires_key_id
        )
        return DoorPassResult(
            allowed=True,
            consumed_key=True,
            was_open=False,
            message="You used a key to open the door.",
        )
