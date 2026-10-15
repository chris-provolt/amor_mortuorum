"""Relics of the Veil: passive totals from the collection and their application."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from ..data import PASSIVE_KEYS, GameData, RelicDef
from ..persistence import MetaState
from .run import Run

logger = logging.getLogger(__name__)

PASSIVE_LABELS = {
    "atk": "ATK",
    "df": "DEF",
    "spd": "SPD",
    "fov": "sight",
    "gold_pct": "gold",
    "xp_pct": "XP",
}


def passive_totals(meta: MetaState, data: GameData) -> Dict[str, int]:
    """Sum every collected relic's passive bonuses."""
    totals: Dict[str, int] = {}
    for relic in data.relics:
        if not meta.relics.has(relic.id):
            continue
        for key, value in relic.passive.items():
            totals[key] = totals.get(key, 0) + value
    return {k: v for k, v in totals.items() if v}


def apply_passives(run: Run, meta: MetaState, data: GameData) -> Dict[str, int]:
    """Refresh every party member's derived bonuses from the relic collection."""
    totals = passive_totals(meta, data)
    for member in run.party:
        member.bonuses = dict(totals)
    return totals


def describe_passive(passive: Dict[str, int]) -> str:
    parts: List[str] = []
    for key in PASSIVE_KEYS:
        value = passive.get(key)
        if not value:
            continue
        label = PASSIVE_LABELS.get(key, key)
        suffix = "%" if key.endswith("_pct") else ""
        parts.append(f"{label} +{value}{suffix}")
    return ", ".join(parts)


def collection_rows(meta: MetaState, data: GameData) -> List[Tuple[RelicDef, bool]]:
    """Every relic in display order with whether it has been collected."""
    return [(relic, meta.relics.has(relic.id)) for relic in data.relics]


__all__ = [
    "passive_totals",
    "apply_passives",
    "describe_passive",
    "collection_rows",
]
