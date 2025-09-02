from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class RandomProvider:
    """
    Thin wrapper around random.Random to make RNG deterministic and injectable
    for tests while avoiding global state.
    """

    seed: Optional[int] = None

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq):  # pragma: no cover - not used in current tests
        return self._rng.choice(seq)
