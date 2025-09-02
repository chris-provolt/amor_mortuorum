from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class RunState:
    """Mutable state of the current run.

    Attributes:
        floor: current dungeon floor (1..99). Use 0 or negative for non-dungeon contexts (e.g., hub), if desired.
        rng: deterministic PRNG for the run; seed for testability.
    """

    floor: int = 1
    rng: random.Random = field(default_factory=random.Random)

    @classmethod
    def with_seed(cls, floor: int, seed: int) -> "RunState":
        rng = random.Random(seed)
        return cls(floor=floor, rng=rng)
