from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class RNG:
    """
    Deterministic-friendly RNG wrapper around random.Random.

    Allows injecting a fixed seed for reproducible tests and game logic. Exposes
    a minimal API used by other modules to avoid tight coupling to Python's
    global RNG.
    """

    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def random(self) -> float:
        """Return the next random float in the range [0.0, 1.0)."""
        return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        """Return a random float N such that a <= N <= b."""
        return self._rng.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        """Return a random integer N such that a <= N <= b."""
        return self._rng.randint(a, b)

    def choice(self, seq):
        """Choose a random element from a non-empty sequence."""
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        return seq[self._rng.randrange(len(seq))]

    def state(self):
        """Return the internal PRNG state for debugging or persistence."""
        return self._rng.getstate()

    def set_state(self, state) -> None:
        """Restore the internal PRNG state."""
        self._rng.setstate(state)
