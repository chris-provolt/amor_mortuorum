from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RandomSource:
    """
    A thin wrapper around random.Random to:
    - centralize RNG handling
    - support optional deterministic seeding for tests
    - provide helper for weighted choice
    """

    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            self._rng = random.Random(self.seed)
            logger.debug("Initialized RandomSource with deterministic seed=%s", self.seed)
        else:
            # Non-deterministic seed using system random state
            self._rng = random.Random()
            logger.debug("Initialized RandomSource with non-deterministic seed")

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: Iterable[Any]) -> Any:
        seq_list = list(seq)
        if not seq_list:
            raise ValueError("RandomSource.choice() received an empty sequence")
        idx = self._rng.randrange(0, len(seq_list))
        return seq_list[idx]

    def weighted_choice(self, weights: Dict[Any, float]) -> Any:
        """
        Select a key from a dictionary of weights where values are non-negative numbers.
        If all weights are zero, raises ValueError.
        """
        if not weights:
            raise ValueError("weighted_choice requires a non-empty weights mapping")

        keys: List[Any] = []
        cumulative: List[float] = []
        total = 0.0
        for k, w in weights.items():
            if w < 0:
                raise ValueError(f"Weight for {k!r} must be non-negative, got {w}")
            if w == 0:
                continue
            total += w
            keys.append(k)
            cumulative.append(total)

        if total == 0:
            raise ValueError("All weights are zero; cannot make a weighted choice")

        r = self._rng.random() * total
        # Find first cumulative >= r
        for i, c in enumerate(cumulative):
            if r <= c:
                return keys[i]
        # Fallback (shouldn't happen due to rounding), return last
        return keys[-1]


__all__ = ["RandomSource"]
