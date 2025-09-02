from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from amor.progression.leveling import Character, LevelingSystem

logger = logging.getLogger(__name__)


@dataclass
class Enemy:
    name: str
    xp: int


@dataclass
class BattleResult:
    enemies: List[Enemy]

    @property
    def total_xp(self) -> int:
        return sum(e.xp for e in self.enemies)


def distribute_xp(total_xp: int, recipients: List[Character]) -> Dict[str, int]:
    """Evenly distribute XP across recipients, assign remainder starting from first.

    Returns a mapping of character.name -> xp_awarded.
    """
    if total_xp <= 0 or not recipients:
        return {c.name: 0 for c in recipients}
    n = len(recipients)
    each = total_xp // n
    remainder = total_xp % n
    awards: Dict[str, int] = {}
    for i, c in enumerate(recipients):
        awards[c.name] = each + (1 if i < remainder else 0)
    return awards


def apply_battle_xp(leveling: LevelingSystem, party: List[Character], result: BattleResult, alive_only: bool = True) -> Dict[str, Tuple[int, int]]:
    """Award XP to the party based on battle result.

    Returns mapping of character.name -> (xp_awarded, levels_gained).
    """
    recipients = [c for c in party if (c.alive or not alive_only)]
    awards: Dict[str, Tuple[int, int]] = {c.name: (0, 0) for c in party}
    if not recipients:
        logger.info("No eligible recipients for XP.")
        return awards
    total = result.total_xp
    split = distribute_xp(total, recipients)
    for c in recipients:
        xp_awarded = split.get(c.name, 0)
        res = leveling.add_xp(c, xp_awarded)
        awards[c.name] = (xp_awarded, res.levels_gained)
    # Non-recipients remain zeros
    return awards
