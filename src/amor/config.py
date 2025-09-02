from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Central game configuration and helpers.

    - encounter_rates: probability per tile movement to trigger an encounter by *tier*.
    - tier_breakpoints: mapping of tier -> inclusive floor range (start, end). Used to compute
      the tier for a given floor. If not provided, sensible defaults are used.
    - encounters_in_hub: whether random encounters are allowed in hub scenes (Graveyard).
    """

    encounter_rates: Dict[int, float] = field(default_factory=lambda: {
        1: 0.02,  # floors 1-20
        2: 0.03,  # floors 21-40
        3: 0.04,  # floors 41-60
        4: 0.05,  # floors 61-80
        5: 0.06,  # floors 81-99
    })
    tier_breakpoints: Dict[int, tuple[int, int]] = field(default_factory=lambda: {
        1: (1, 20),
        2: (21, 40),
        3: (41, 60),
        4: (61, 80),
        5: (81, 99),
    })
    encounters_in_hub: bool = False

    def get_tier_for_floor(self, floor: int) -> Optional[int]:
        """Return the tier for a given floor using configured breakpoints.

        Returns None if the floor does not fall in any configured tier.
        """
        for tier, (start, end) in self.tier_breakpoints.items():
            if start <= floor <= end:
                return tier
        return None

    def get_encounter_rate_for_floor(self, floor: int) -> float:
        """Return encounter probability for a given floor using tier mapping.

        If tier resolution fails, returns a default safe value of 0.0 and logs a warning.
        """
        tier = self.get_tier_for_floor(floor)
        if tier is None:
            logger.warning("No tier configured for floor %s; defaulting to 0.0 encounter rate", floor)
            return 0.0
        rate = self.encounter_rates.get(tier, 0.0)
        # Clamp to [0, 1] for safety
        if rate < 0.0 or rate > 1.0:
            logger.error("Encounter rate out of bounds for tier %s: %s. Clamping to [0,1].", tier, rate)
            return max(0.0, min(1.0, rate))
        return rate

    @classmethod
    def from_json(cls, path: Path) -> "GameConfig":
        """Load configuration from JSON file. Missing fields fallback to defaults."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        cfg = cls()
        if "encounter_rates" in raw:
            # Convert keys to int (JSON keys are strings)
            cfg.encounter_rates = {int(k): float(v) for k, v in raw["encounter_rates"].items()}
        if "tier_breakpoints" in raw:
            cfg.tier_breakpoints = {
                int(k): (int(v[0]), int(v[1])) for k, v in raw["tier_breakpoints"].items()
            }
        if "encounters_in_hub" in raw:
            cfg.encounters_in_hub = bool(raw["encounters_in_hub"])
        return cfg

    def to_json(self, path: Path) -> None:
        """Persist configuration to a JSON file."""
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "encounter_rates": self.encounter_rates,
                    "tier_breakpoints": self.tier_breakpoints,
                    "encounters_in_hub": self.encounters_in_hub,
                },
                f,
                indent=2,
                sort_keys=True,
            )
