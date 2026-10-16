"""Lifetime statistics and achievements, kept in ``MetaState``.

Scenes call ``bump`` at the moments that matter; ``check_achievements``
turns the counters into unlocks. Both are pure and cheap.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from ..data import AchievementDef, GameData
from ..persistence import MetaState

logger = logging.getLogger(__name__)

STAT_LABELS: Dict[str, str] = {
    "runs_started": "Runs started",
    "runs_won": "Runs won",
    "deaths": "Deaths",
    "revives": "Token revives",
    "deepest_floor": "Deepest floor",
    "battles_won": "Battles won",
    "enemies_slain": "Enemies slain",
    "bosses_slain": "Bosses slain",
    "chests_opened": "Chests opened",
    "gold_earned": "Gold earned",
    "steps": "Steps taken",
    "relics": "Relics found",
    "bounties": "Bounties claimed",
    "ambushes": "Sleepers slain",
}


def bump(meta: MetaState, key: str, amount: int = 1) -> int:
    """Increase a counter and return its new value."""
    meta.stats[key] = meta.stats.get(key, 0) + int(amount)
    return meta.stats[key]


def record_max(meta: MetaState, key: str, value: int) -> int:
    meta.stats[key] = max(meta.stats.get(key, 0), int(value))
    return meta.stats[key]


def derived_stats(meta: MetaState) -> Dict[str, int]:
    """Counters plus values that live elsewhere in meta (relics, deepest floor)."""
    out = dict(meta.stats)
    out["relics"] = len(meta.relics.collected)
    out["deepest_floor"] = max(out.get("deepest_floor", 0), meta.deepest_floor)
    out.setdefault("runs_won", meta.runs_completed if "runs_won" not in out else out["runs_won"])
    return out


def check_achievements(meta: MetaState, data: GameData) -> List[AchievementDef]:
    """Unlock every achievement whose condition now holds; return the new ones."""
    values = derived_stats(meta)
    unlocked: List[AchievementDef] = []
    for ach in data.achievements:
        if ach.id in meta.achievements:
            continue
        if values.get(ach.stat, 0) >= ach.at_least:
            meta.achievements.add(ach.id)
            unlocked.append(ach)
            logger.info("Achievement unlocked: %s", ach.name)
    return unlocked


def stat_rows(meta: MetaState) -> List[tuple]:
    values = derived_stats(meta)
    return [(label, values.get(key, 0)) for key, label in STAT_LABELS.items()]


__all__ = ["STAT_LABELS", "bump", "record_max", "derived_stats", "check_achievements", "stat_rows"]
