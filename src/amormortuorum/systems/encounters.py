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

ENCOUNTER_CAP = 0.35


def encounter_chance(step_chance: float, steps_since_last: int) -> float:
    """Per-step encounter probability after ``steps_since_last`` quiet steps."""
    return min(ENCOUNTER_CAP, step_chance * (1 + 0.1 * max(0, steps_since_last)))


def step_encounter(rng: Random, floor: int, steps_since_last: int, data: GameData) -> bool:
    """Roll whether a step on ``floor`` triggers an encounter."""
    tier = data.tier_for_floor(floor)
    step_chance = data.encounters[tier.name].step_chance
    return rng.random() < encounter_chance(step_chance, steps_since_last)


def roll_formation(rng: Random, floor: int, data: GameData) -> List[Enemy]:
    """Pick a weighted enemy formation for the floor's tier and instantiate it."""
    tier = data.tier_for_floor(floor)
    formations = data.encounters[tier.name].formations
    weights = [max(0, f.weight) for f in formations]
    chosen = rng.choices(formations, weights=weights, k=1)[0]
    return [Enemy.from_def(data.enemy(enemy_id)) for enemy_id in chosen.enemies]


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
    "encounter_rng",
    "combat_rng",
]
