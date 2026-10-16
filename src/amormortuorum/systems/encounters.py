"""Random encounters while exploring a floor.

The chance of an encounter grows with each step taken since the last one, so
long quiet stretches are rarer, but it never exceeds ``ENCOUNTER_CAP``.
"""
from __future__ import annotations

from random import Random
from typing import List

from ..data import GameData
from .entities import Enemy
from .rng import stream_rng

ENCOUNTER_CAP = 0.2  # default; data/balance.json overrides
ENCOUNTER_GROWTH = 0.05


def encounter_chance(
    step_chance: float,
    steps_since_last: int,
    cap: float = ENCOUNTER_CAP,
    growth: float = ENCOUNTER_GROWTH,
) -> float:
    """Per-step encounter probability after ``steps_since_last`` quiet steps."""
    return min(cap, step_chance * (1 + growth * max(0, steps_since_last)))


def step_encounter(rng: Random, floor: int, steps_since_last: int, data: GameData) -> bool:
    """Roll whether a step on ``floor`` triggers an encounter."""
    tier = data.tier_for_floor(floor)
    step_chance = data.encounters[tier.name].step_chance
    b = data.balance
    return rng.random() < encounter_chance(
        step_chance, steps_since_last, b.encounter_cap, b.encounter_growth_per_step
    )


def roll_formation(rng: Random, floor: int, data: GameData) -> List[Enemy]:
    """Pick a weighted formation for the floor's tier, scaled to the floor's depth."""
    tier = data.tier_for_floor(floor)
    formations = data.encounters[tier.name].formations
    weights = [max(0, f.weight) for f in formations]
    chosen = rng.choices(formations, weights=weights, k=1)[0]
    return [Enemy.from_def(data.enemy(eid), floor, data.balance) for eid in chosen.enemies]


def boss_formation(floor: int, data: GameData) -> List[Enemy]:
    """The boss party for ``floor`` (empty if the floor has no boss)."""
    boss = data.boss_for_floor(floor)
    if boss is None:
        return []
    return [Enemy.from_def(data.enemy(eid), floor, data.balance) for eid in boss.enemies]


def encounter_rng(seed: int, floor: int) -> Random:
    """Stream used for encounter rolls and formation picks on a floor."""
    return stream_rng(seed, floor, "encounters")


def combat_rng(seed: int, floor: int, encounter_index: int) -> Random:
    """Stream used inside the ``encounter_index``-th battle on a floor."""
    return stream_rng(seed, floor, f"combat:{encounter_index}")


__all__ = [
    "ENCOUNTER_CAP",
    "encounter_chance",
    "step_encounter",
    "roll_formation",
    "boss_formation",
    "encounter_rng",
    "combat_rng",
]
