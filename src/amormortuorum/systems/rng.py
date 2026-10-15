"""Seeded random streams so every roll in a run is reproducible from one seed.

The formulas for floor and chest streams are part of the public design (see
README "Testing & Determinism"); do not change them without bumping the save
schema, because replaying a seed is a promised feature.
"""
from __future__ import annotations

from random import Random

FLOOR_STRIDE = 1013
CHEST_STRIDE = 13


def floor_rng(seed: int, floor: int) -> Random:
    """Stream used for floor layout (rooms, corridors, features, portal roll)."""
    return Random(seed + floor * FLOOR_STRIDE)


def chest_rng(seed: int, floor: int) -> Random:
    """Stream used for chest contents on a floor."""
    return Random(seed + floor * CHEST_STRIDE)


def stream_rng(seed: int, floor: int, stream: str) -> Random:
    """Named stream (``"encounters"``, ``"combat"``, ``"flee"``...) for a floor.

    Keyed by string so adding a new stream never shifts an existing one.
    """
    return Random(f"{seed}:{floor}:{stream}")


def random_seed() -> int:
    """A fresh, non-deterministic seed for a new run (31-bit for easy typing)."""
    from random import SystemRandom

    return SystemRandom().randrange(1, 2**31)
