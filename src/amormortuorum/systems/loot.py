"""Loot rolls: chest quality by floor tier, item pick, gold drops."""
from __future__ import annotations

from random import Random
from typing import Dict, List, Optional

from ..data import QUALITIES, GameData, ItemDef


def tier_for_floor(floor: int, data: GameData) -> str:
    return data.tier_for_floor(floor).name


def roll_quality(rng: Random, weights: Dict[str, int]) -> str:
    """Pick a quality bucket from ``{quality: weight}``."""
    names: List[str] = [q for q in QUALITIES if weights.get(q, 0) > 0]
    if not names:
        raise ValueError("quality weights must have at least one positive entry")
    return rng.choices(names, weights=[weights[q] for q in names], k=1)[0]


def _fallback_qualities(quality: str) -> List[str]:
    """The requested quality first, then each lower quality, then higher ones."""
    idx = QUALITIES.index(quality)
    lower = list(reversed(QUALITIES[:idx]))
    higher = list(QUALITIES[idx + 1:])
    return [quality, *lower, *higher]


def roll_chest(rng: Random, floor: int, data: GameData) -> ItemDef:
    """Roll the contents of a chest on ``floor`` from the tier's quality weights."""
    tier = tier_for_floor(floor, data)
    quality = roll_quality(rng, data.loot_tables[tier])
    for q in _fallback_qualities(quality):
        pool = sorted(
            (it for it in data.items_of_quality(q) if it.type != "key"), key=lambda it: it.id
        )
        if pool:
            return rng.choice(pool)
    raise ValueError("no items defined in data")


def roll_gold(rng: Random, floor: int) -> int:
    """Gold from a chest or a rare drop; grows roughly linearly with depth."""
    base = 5 + floor * 2
    return rng.randint(base, base * 2)


def roll_chest_gold(rng: Random, floor: int, chance: float = 0.25) -> Optional[int]:
    """Some chests hold gold instead of an item. Returns the amount or ``None``."""
    if rng.random() < chance:
        return roll_gold(rng, floor)
    return None
