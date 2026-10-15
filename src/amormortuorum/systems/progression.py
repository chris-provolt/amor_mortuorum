"""XP and levelling: level is always derived from total XP via the data curve."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..data import GameData
from .entities import Player

logger = logging.getLogger(__name__)


@dataclass
class LevelUp:
    level: int
    gains: Dict[str, int] = field(default_factory=dict)

    def describe(self) -> str:
        parts = [f"{k.upper().replace('MAX_', 'MAX ')} +{v}" for k, v in self.gains.items() if v]
        return f"Level {self.level}! " + ", ".join(parts)


def xp_to_next_level(player: Player, data: GameData) -> Optional[int]:
    """XP still needed for the next level, or ``None`` at the cap."""
    curve = data.xp_curve
    if player.level >= curve.max_level:
        return None
    return max(0, curve.xp_for_level(player.level + 1) - player.xp)


def _gains_for_level(level: int, data: GameData) -> Dict[str, int]:
    curve = data.xp_curve
    gains = dict(curve.per_level)
    gains["spd"] = gains.get("spd", 0) + (1 if level % curve.spd_every == 0 else 0)
    return {k: v for k, v in gains.items() if v}


def sync_level(player: Player, data: GameData) -> List[LevelUp]:
    """Raise ``player.level`` to match ``player.xp``; apply stat gains per level gained.

    Idempotent: calling it again without new XP returns an empty list. Each
    level adds its gains to the base stats and heals by the HP/MP gained.
    """
    curve = data.xp_curve
    target = curve.level_for_xp(player.xp)
    ups: List[LevelUp] = []
    while player.level < target:
        player.level += 1
        gains = _gains_for_level(player.level, data)
        s = player.stats
        s.max_hp += gains.get("max_hp", 0)
        s.hp += gains.get("max_hp", 0)
        s.max_mp += gains.get("max_mp", 0)
        s.mp += gains.get("max_mp", 0)
        s.atk += gains.get("atk", 0)
        s.df += gains.get("df", 0)
        s.spd += gains.get("spd", 0)
        ups.append(LevelUp(level=player.level, gains=gains))
        logger.info("%s reached level %d: %s", player.name, player.level, gains)
    return ups


def grant_xp(player: Player, amount: int, data: GameData) -> List[LevelUp]:
    """Add XP and resolve any level-ups it causes."""
    if amount < 0:
        raise ValueError("XP amount must be non-negative")
    player.xp += amount
    return sync_level(player, data)


__all__ = ["LevelUp", "xp_to_next_level", "sync_level", "grant_xp"]
