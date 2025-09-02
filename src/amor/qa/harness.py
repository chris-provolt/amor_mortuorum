from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar

from ..core.seed import SeedManager

T = TypeVar("T")


@dataclass
class QATrace:
    seed: Optional[int]
    events: List[Dict[str, Any]]
    checksum: str


class QAHarness:
    """
    Deterministic QA harness that records RNG-driven operations and can verify reproduction.

    Use this to create reproducible scenarios for procedural generation, combat rolls, etc.
    """

    def __init__(self, seed_manager: Optional[SeedManager] = None):
        self.seed_manager = seed_manager or SeedManager()
        self._events: List[Dict[str, Any]] = []

    # Recording helpers

    def _record(self, op: str, args: Dict[str, Any], result: Any) -> None:
        ev = {"op": op, "args": args, "result": result}
        self._events.append(ev)

    # Deterministic wrappers around RNG operations

    def randint(self, a: int, b: int) -> int:
        val = self.seed_manager.randint(a, b)
        self._record("randint", {"a": a, "b": b}, val)
        return val

    def random(self) -> float:
        val = self.seed_manager.random()
        self._record("random", {}, val)
        return val

    def choice(self, seq: Sequence[T]) -> T:
        val = self.seed_manager.choice(seq)
        self._record("choice", {"seq": list(seq)}, val)
        return val

    def sample(self, seq: Sequence[T], k: int) -> List[T]:
        val = self.seed_manager.sample(seq, k)
        self._record("sample", {"seq": list(seq), "k": k}, list(val))
        return val

    def shuffle(self, seq: List[T]) -> List[T]:
        copy = list(seq)
        self.seed_manager.shuffle(copy)
        self._record("shuffle", {"seq": list(seq)}, list(copy))
        return copy

    def spawn_id(self) -> str:
        """Return a deterministic identifier from RNG stream (hex)."""
        x = self.randint(0, 2**31 - 1)
        val = f"{x:08x}"
        self._record("spawn_id", {}, val)
        return val

    # Trace management

    def _compute_checksum(self, events: List[Dict[str, Any]]) -> str:
        m = hashlib.sha256()
        m.update(json.dumps(events, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return m.hexdigest()

    def snapshot(self) -> QATrace:
        ch = self._compute_checksum(self._events)
        trace = QATrace(seed=self.seed_manager.seed, events=list(self._events), checksum=ch)
        return trace

    def clear(self) -> None:
        self._events.clear()

    # Verification

    def reproduce(self, trace: QATrace) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Re-run the trace deterministically and compare results.

        Returns (ok, mismatch_info). If mismatch, info contains index and details.
        """
        # Fresh seed manager for reproduction
        sm = SeedManager()
        if trace.seed is not None:
            sm.set_seed(trace.seed)
        repro = QAHarness(seed_manager=sm)
        # Replay operations
        for idx, ev in enumerate(trace.events):
            op = ev["op"]
            args = ev["args"]
            expected = ev["result"]
            if op == "randint":
                got = repro.randint(args["a"], args["b"])  # type: ignore
            elif op == "random":
                got = repro.random()
            elif op == "choice":
                got = repro.choice(args["seq"])  # type: ignore
            elif op == "sample":
                got = repro.sample(args["seq"], args["k"])  # type: ignore
            elif op == "shuffle":
                got = repro.shuffle(args["seq"])  # type: ignore
            elif op == "spawn_id":
                got = repro.spawn_id()
            else:
                return False, {"index": idx, "error": f"Unknown op {op}"}

            # Compare allowing float tolerance for random()
            if isinstance(expected, float):
                if abs(got - expected) > 1e-12:
                    return False, {"index": idx, "op": op, "expected": expected, "got": got}
            else:
                if got != expected:
                    return False, {"index": idx, "op": op, "expected": expected, "got": got}
        # Check checksum too
        ch = repro._compute_checksum(repro._events)
        if ch != trace.checksum:
            return False, {"error": "checksum", "expected": trace.checksum, "got": ch}
        return True, None

    # Serialization helpers

    @staticmethod
    def to_json(trace: QATrace) -> str:
        return json.dumps(asdict(trace), separators=(",", ":"))

    @staticmethod
    def from_json(data: str) -> QATrace:
        obj = json.loads(data)
        return QATrace(seed=obj.get("seed"), events=obj.get("events", []), checksum=obj.get("checksum", ""))
