"""Shared, arcade-free application state handed to every scene."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from ..persistence import MetaState, SaveManager
from .settings import Settings

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from ..data import GameData
    from ..systems.run import Run


@dataclass
class GameContext:
    """Everything a scene needs that is not the window itself.

    - ``settings``: loaded user/default settings
    - ``save_manager``: persistence entry point for the active profile
    - ``data``: static game data (items, enemies, tables); set once at boot
    - ``meta``: persistent meta progression (relics, crypt); loaded at boot
    - ``run``: the active run, or ``None`` while on the main menu
    - ``seed``: seed requested on the command line, or ``None`` for random
    """

    settings: Settings
    save_manager: SaveManager
    data: Optional["GameData"] = None
    meta: MetaState = field(default_factory=MetaState)
    run: Optional["Run"] = None
    seed: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)
