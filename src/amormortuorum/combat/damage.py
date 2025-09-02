from __future__ import annotations

import logging
import random
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DamageBreakdown:
    """Details of a computed damage roll.

    Attributes:
        base: The base damage before RNG (max(1, atk - df)).
        multiplier: The RNG multiplier applied to base damage.
        rolled: The raw rolled value (base * multiplier) before flooring/min bound.
        final: The final integer damage applied (>= 1).
    """

    base: int
    multiplier: float
    rolled: float
    final: int


class DamageCalculator:
    """Compute damage for a basic attack using ATK, DF, and RNG variance.

    The formula is:
      base = max(1, atk - df)
      multiplier ~ Uniform(1 - variance, 1 + variance)
      damage = max(1, round(base * multiplier))

    Notes:
    - A strict floor at 1 damage is enforced.
    - Variance defines the ± range of RNG applied multiplicatively.
    - Variance of 0.10 means ±10% spread (0.90 to 1.10 multiplier).
    """

    def __init__(self, variance: float = 0.10) -> None:
        if not (0.0 <= variance <= 0.75):
            # Guard extreme values; large variance can cause feel-bad swings.
            raise ValueError("variance must be between 0.0 and 0.75")
        self.variance = float(variance)

    def compute_damage(self, atk: int, df: int, rng: random.Random | None = None) -> int:
        """Compute final damage.

        Args:
            atk: Attacker's attack stat (non-negative integer expected).
            df: Defender's defense stat (non-negative integer expected).
            rng: Optional random number generator to ensure determinism (tests).

        Returns:
            Final integer damage, floor at 1.
        """
        breakdown = self.compute_damage_with_breakdown(atk, df, rng)
        return breakdown.final

    def compute_damage_with_breakdown(
        self, atk: int, df: int, rng: random.Random | None = None
    ) -> DamageBreakdown:
        """Compute damage and return a detailed breakdown for debugging/tests."""
        if atk is None or df is None:
            raise ValueError("atk and df must be provided")
        try:
            atk_i = int(atk)
            df_i = int(df)
        except Exception as exc:
            raise ValueError("atk and df must be integers or castable to int") from exc
        if atk_i < 0 or df_i < 0:
            # Clamp negatives to zero with a warning; negative stats are not supported.
            logger.warning("Negative stat detected (atk=%s, df=%s); clamping to zero.", atk_i, df_i)
            atk_i = max(0, atk_i)
            df_i = max(0, df_i)

        base = max(1, atk_i - df_i)

        if self.variance == 0.0:
            multiplier = 1.0
        else:
            rng = rng or random.Random()
            low = 1.0 - self.variance
            high = 1.0 + self.variance
            multiplier = rng.uniform(low, high)

        rolled = base * multiplier
        final = max(1, int(round(rolled)))

        return DamageBreakdown(base=base, multiplier=multiplier, rolled=rolled, final=final)
