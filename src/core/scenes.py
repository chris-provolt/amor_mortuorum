from __future__ import annotations

from enum import Enum


class SceneType(str, Enum):
    """Enumeration of high-level game scenes for ambient music routing.

    - HUB: Graveyard hub area
    - DUNGEON: Exploration floors
    - COMBAT: Turn-based battle
    """

    HUB = "hub"
    DUNGEON = "dungeon"
    COMBAT = "combat"

    @classmethod
    def from_string(cls, value: str) -> "SceneType":
        value = value.strip().lower()
        return cls(value)
