from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Command(str, Enum):
    """Available combat commands.

    These map to the classic FF1-style menu.
    """

    ATTACK = "Attack"
    SKILL = "Skill"
    ITEM = "Item"
    DEFEND = "Defend"
    FLEE = "Flee"


@dataclass(frozen=True)
class Action:
    """Represents a player's selected action.

    For commands that do not require a target, target_id will be None.
    """

    command: Command
    target_id: Optional[str] = None
