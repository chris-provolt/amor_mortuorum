from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class XPCurve:
    """Represents an XP curve mapping levels to cumulative XP thresholds.

    Level indexing:
    - Level 1 threshold is always 0 cumulative XP.
    - thresholds[level] = total cumulative XP required to reach that level.
      thresholds[1] == 0.
    - The last level is the level cap; there is no threshold to go beyond it.
    """

    thresholds: List[int]

    def __post_init__(self) -> None:
        if not self.thresholds or len(self.thresholds) < 2:
            raise ValueError("XPCurve requires at least thresholds for levels 1 and 2")
        if self.thresholds[1] != 0:
            raise ValueError("Threshold for level 1 must be 0")
        # Ensure non-decreasing
        for i in range(2, len(self.thresholds)):
            if self.thresholds[i] < self.thresholds[i - 1]:
                raise ValueError("XP thresholds must be non-decreasing")

    @property
    def max_level(self) -> int:
        return len(self.thresholds) - 1

    def total_xp_for_level(self, level: int) -> int:
        if level < 1:
            raise ValueError("Level must be >= 1")
        level = min(level, self.max_level)
        return self.thresholds[level]

    def xp_to_next(self, level: int) -> Optional[int]:
        """Returns XP required to advance from current level to next level.
        Returns None if at cap.
        """
        if level >= self.max_level:
            return None
        return self.thresholds[level + 1] - self.thresholds[level]

    def level_for_total_xp(self, total_xp: int) -> int:
        """Binary search to find level corresponding to total XP.
        Returns highest level such that thresholds[level] <= total_xp.
        """
        lo, hi = 1, self.max_level
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.thresholds[mid] <= total_xp:
                lo = mid + 1
            else:
                hi = mid - 1
        return hi

    @staticmethod
    def from_file(path: str) -> "XPCurve":
        """Load XPCurve from a JSON file.

        Supported formats:
        1) Parametric:
           {
             "schema": "xp_curve@1",
             "mode": "parametric",
             "params": {"base_to_next": 25, "growth": 1.12, "levels": 99}
           }

        2) Thresholds (cumulative):
           {
             "schema": "xp_curve@1",
             "mode": "thresholds",
             "thresholds": [null, 0, 25, 53, ...]  // index 0 unused, 1..N levels
           }
        """
        if not os.path.exists(path):
            logger.warning("XP curve file %s not found. Falling back to defaults.", path)
            return XPCurve.generate_parametric()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return XPCurve.from_dict(data)

    @staticmethod
    def from_dict(data: Dict) -> "XPCurve":
        schema = data.get("schema")
        if schema != "xp_curve@1":
            logger.warning("Unexpected XP curve schema %s; continuing anyway", schema)
        mode = data.get("mode", "parametric")
        if mode == "parametric":
            params = data.get("params", {})
            base = float(params.get("base_to_next", 25))
            growth = float(params.get("growth", 1.12))
            levels = int(params.get("levels", 99))
            return XPCurve.generate_parametric(base, growth, levels)
        elif mode == "thresholds":
            thresholds = data.get("thresholds")
            if not isinstance(thresholds, list):
                raise ValueError("thresholds must be a list when mode is 'thresholds'")
            # Some authors may omit index 0; ensure thresholds[1] exists and index 0 placeholder
            if len(thresholds) > 0 and thresholds[0] is not None:
                # If author mistakenly included a value at index 0, prepend a dummy to realign
                thresholds = [None] + thresholds
            # Replace None at index 0
            if thresholds[0] is None:
                thresholds[0] = 0
            # Type cast to int and validate
            t_int: List[int] = []
            for i, v in enumerate(thresholds):
                if i == 0:
                    t_int.append(0)
                else:
                    if v is None:
                        raise ValueError(f"Missing threshold for level {i}")
                    t_int.append(int(v))
            return XPCurve(t_int)
        else:
            raise ValueError(f"Unknown XP curve mode: {mode}")

    @staticmethod
    def generate_parametric(base_to_next: float = 25.0, growth: float = 1.12, levels: int = 99) -> "XPCurve":
        """Generate a parametric XP curve. Level 1 threshold is 0.
        xp_to_next(L) = round(base * growth^(L-1)) for L >= 1 (to get to L+1)
        cumulative thresholds are summed from xp_to_next.
        """
        if levels < 2:
            raise ValueError("levels must be >= 2")
        thresholds: List[int] = [0] * (levels + 1)
        thresholds[1] = 0
        cumulative = 0
        for L in range(1, levels):
            to_next = int(round(base_to_next * (growth ** (L - 1))))
            cumulative += to_next
            thresholds[L + 1] = cumulative
        return XPCurve(thresholds)
