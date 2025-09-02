from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import secrets
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

logger = logging.getLogger(__name__)


def _to_stable_json(value: Any) -> str:
    """Stable JSON encoding for hashing.

    Ensures consistent ordering and representation across runs and Python versions
    (for basic types). This is critical to make seed derivation deterministic.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class RNGManager:
    """Central deterministic RNG manager.

    Provides domain- and context-specific RNGs derived from a master seed, ensuring
    reproducible results regardless of call ordering.

    Usage pattern:
        rngm = RNGManager(master_seed)
        floor_rng = rngm.context_rng("floor_layout", floor)
        loot_rng = rngm.context_rng("chest_loot", floor, chest_x, chest_y)

    The master seed can be an int, str, or bytes. It will be canonicalized to bytes
    and used to derive 64-bit integer seeds via BLAKE2b for downstream random.Random
    instances.
    """

    master_seed: Union[int, str, bytes, None]

    def __post_init__(self) -> None:
        # Canonicalize master seed to bytes
        object.__setattr__(self, "_master_seed_bytes", self._canonicalize_seed(self.master_seed))
        if self.master_seed is None:
            # If no seed is provided, create a random one and store its bytes.
            rand = secrets.token_bytes(16)
            object.__setattr__(self, "_master_seed_bytes", rand)
            logger.info("No master seed provided; generated random seed: %s", rand.hex())
        else:
            logger.debug("Using master seed: %r", self.master_seed)

    @staticmethod
    def _canonicalize_seed(seed: Optional[Union[int, str, bytes]]) -> bytes:
        if seed is None:
            return b""
        if isinstance(seed, bytes):
            return seed
        if isinstance(seed, int):
            # Convert int to bytes (big-endian, minimal length)
            length = (seed.bit_length() + 7) // 8 or 1
            return seed.to_bytes(length, "big", signed=False)
        if isinstance(seed, str):
            # Allow hex-like strings or raw strings
            s = seed.strip()
            if s.startswith("0x"):
                try:
                    val = int(s, 16)
                    length = (val.bit_length() + 7) // 8 or 1
                    return val.to_bytes(length, "big", signed=False)
                except ValueError:
                    return s.encode("utf-8")
            # else interpret as utf-8
            return s.encode("utf-8")
        raise TypeError("Unsupported seed type: %r" % (type(seed),))

    def derive_seed(self, domain: str, *identifiers: Any) -> int:
        """Derive a 64-bit integer seed from master seed and domain identifiers.

        Domain examples: "floor_layout", "encounter_table", "chest_loot".
        Identifiers can be floor index, coordinates, player id, etc.
        """
        # Construct a stable payload
        payload = {
            "domain": domain,
            "ids": identifiers,
            "master": self._master_seed_bytes.hex(),
            "algo": "blake2b-64",
            "version": 1,
        }
        data = _to_stable_json(payload).encode("utf-8")
        h = hashlib.blake2b(data, digest_size=8)  # 64-bit seed
        seed_int = int.from_bytes(h.digest(), "big", signed=False)
        logger.debug("Derived seed for domain=%s ids=%s -> %d", domain, identifiers, seed_int)
        return seed_int

    def context_rng(self, domain: str, *identifiers: Any) -> random.Random:
        seed = self.derive_seed(domain, *identifiers)
        rng = random.Random(seed)
        return rng

    def get_master_seed_hex(self) -> str:
        return self._master_seed_bytes.hex()
