"""Loot rolls: chest quality by floor tier, item pick, gold drops."""
from __future__ import annotations

from random import Random
from typing import Dict, Iterable, List, Optional

from ..data import QUALITIES, GameData, ItemDef, RelicDef

# Relics that only bosses award (see bosses.json); the rest can turn up in chests.
RELIC_CHEST_BASE = 0.02
RELIC_CHEST_PER_TIER = 0.015


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


def relic_chest_chance(floor: int, data: GameData) -> float:
    """Chance a chest holds a relic: 2% on T1 rising to 8% on T5."""
    tier_index = data.tiers.index(data.tier_for_floor(floor))
    return RELIC_CHEST_BASE + RELIC_CHEST_PER_TIER * tier_index


def chest_relic_pool(data: GameData, collected: Iterable[str]) -> List[RelicDef]:
    """Relics that chests may still drop: not boss-awarded and not yet collected."""
    boss_relics = {b.relic_id for b in data.bosses.values() if b.relic_id}
    have = set(collected)
    return [r for r in data.relics if r.id not in boss_relics and r.id not in have]


def roll_relic(
    rng: Random, floor: int, data: GameData, collected: Iterable[str]
) -> Optional[RelicDef]:
    """Roll whether a chest on ``floor`` yields one of the remaining chest relics."""
    pool = chest_relic_pool(data, collected)
    if not pool:
        return None
    if rng.random() >= relic_chest_chance(floor, data):
        return None
    return rng.choice(pool)
