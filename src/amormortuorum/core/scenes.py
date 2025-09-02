from __future__ import annotations

from enum import Enum


class Scene(str, Enum):
    """Game scenes/states that drive high-level behavior.

    This enum is intentionally minimal to avoid coupling to the rendering stack.
    Use it anywhere you need to express the current context (e.g., to enforce
    Graveyard-only saves).
    """

    GRAVEYARD = "graveyard"
    DUNGEON = "dungeon"
    COMBAT = "combat"  # Included for completeness; not used in this feature.
    MENU = "menu"  # Main menu or other non-world UI contexts.
