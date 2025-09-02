from __future__ import annotations

import hashlib
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, TypeVar
import random as _random

T = TypeVar("T")


@dataclass
class SeedState:
    """Serializable snapshot of RNG state."""
    seed: Optional[int]
    internal_state: object


class SeedManager:
    """
    Centralized RNG manager to enforce determinism across the application.

    - Uses a dedicated instance of random.Random; does not mutate global random state.
    - Supports setting seed from int or any string via hashing.
    - Provides utility methods mirroring common random operations.
    - Offers a temporary_seed context manager that restores previous RNG state.
    """

    def __init__(self, seed: Optional[int] = None):
        self._lock = threading.RLock()
        self._rng = _random.Random()
        self._seed: Optional[int] = None
        if seed is not None:
            self.set_seed(seed)
        else:
            # Initialize with system time to avoid identical runs when not specified.
            self._rng.seed()

    def derive_seed(self, source: str) -> int:
        """Derive a 32-bit integer seed from an arbitrary string using SHA256."""
        digest = hashlib.sha256(source.encode("utf-8")).digest()
        # Use first 8 bytes to make a 64-bit int then fold into 32-bit range
        val = int.from_bytes(digest[:8], "big", signed=False)
        return val & 0xFFFFFFFF

    def set_seed(self, seed_or_str: Any) -> int:
        """
        Set the RNG seed. Accepts an int, a string, or any object convertible to string.
        Returns the effective integer seed used.
        """
        with self._lock:
            if isinstance(seed_or_str, int):
                seed = seed_or_str & 0xFFFFFFFF
            else:
                seed = self.derive_seed(str(seed_or_str))
            self._rng.seed(seed)
            self._seed = seed
            return seed

    @property
    def seed(self) -> Optional[int]:
        return self._seed

    @property
    def rng(self) -> _random.Random:
        return self._rng

    def snapshot(self) -> SeedState:
        with self._lock:
            return SeedState(self._seed, self._rng.getstate())

    def restore(self, state: SeedState) -> None:
        with self._lock:
            self._seed = state.seed
            self._rng.setstate(state.internal_state)

    @contextmanager
    def temporary_seed(self, seed_or_str: Any):
        """
        Temporarily set seed for deterministic operation block; restores state afterwards.
        """
        with self._lock:
            snap = self.snapshot()
            try:
                self.set_seed(seed_or_str)
                yield self
            finally:
                self.restore(snap)

    # Delegated random methods with thread-safety wrappers

    def randint(self, a: int, b: int) -> int:
        with self._lock:
            return self._rng.randint(a, b)

    def random(self) -> float:
        with self._lock:
            return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        with self._lock:
            return self._rng.uniform(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        with self._lock:
            return self._rng.choice(seq)

    def choices(self, population: Sequence[T], k: int = 1, weights: Optional[Sequence[float]] = None) -> List[T]:
        with self._lock:
            return self._rng.choices(population, weights=weights, k=k)

    def sample(self, population: Sequence[T], k: int) -> List[T]:
        with self._lock:
            return self._rng.sample(population, k)

    def shuffle(self, x: List[T]) -> None:
        with self._lock:
            self._rng.shuffle(x)

    # Utilities

    def deterministic_uuid5(self, namespace: uuid.UUID, name: str) -> uuid.UUID:
        """Deterministic UUID based on namespace and name; independent of RNG seed."""
        return uuid.uuid5(namespace, name)

    def deterministic_uuid4(self) -> uuid.UUID:
        """
        Deterministic UUID-like value using RNG stream (not a true UUID4 but stable for testing).
        """
        # Compose 16 random bytes using rng
        with self._lock:
            b = bytes(self._rng.getrandbits(8) for _ in range(16))
        # Force version 4 and variant bits to be UUID-like
        lst = list(b)
        lst[6] = (lst[6] & 0x0F) | 0x40
        lst[8] = (lst[8] & 0x3F) | 0x80
        return uuid.UUID(bytes=bytes(lst))


def monotonic_time() -> float:
    """Monotonic time helper for timing measurements."""
    return time.perf_counter()
