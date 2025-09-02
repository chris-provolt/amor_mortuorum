from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from ..core.rng import RNG


@dataclass(frozen=True)
class DamageResult:
    """Detailed combat damage outcome."""
    damage: int
    is_crit: bool
    base: int
    variance_multiplier: float


def compute_damage(
    attacker_atk: int,
    defender_def: int,
    rng: RNG,
    *,
    crit_chance: float = 0.10,
    crit_multiplier: float = 1.5,
    variance: Tuple[float, float] = (0.85, 1.0),
    defense_mitigation: float = 1.0,
) -> DamageResult:
    """
    Compute turn-based damage with variance, defense mitigation, and criticals.

    Formula:
      base = max(1, attacker_atk - floor(defender_def * defense_mitigation))
      var  = uniform(variance[0], variance[1])
      dmg  = floor(base * var)
      if crit: dmg = round(dmg * crit_multiplier)

    Returns DamageResult with details for debugging and testing.
    """
    if attacker_atk < 0 or defender_def < 0:
        raise ValueError("Stats must be non-negative")
    if not (0.0 <= crit_chance <= 1.0):
        raise ValueError("crit_chance must be within [0, 1]")
    if variance[0] <= 0 or variance[1] <= 0 or variance[0] > variance[1]:
        raise ValueError("Invalid variance range")
    if defense_mitigation < 0:
        raise ValueError("defense_mitigation must be >= 0")

    mitigated_def = int(defender_def * defense_mitigation)
    base = attacker_atk - mitigated_def
    if base < 1:
        base = 1

    var_mul = rng.uniform(variance[0], variance[1])
    dmg = int(base * var_mul)
    if dmg < 1:
        dmg = 1

    is_crit = rng.random() < crit_chance
    if is_crit:
        # Round to nearest int for crits to avoid truncation bias
        dmg = int(round(dmg * crit_multiplier))
        if dmg < 1:
            dmg = 1

    return DamageResult(damage=dmg, is_crit=is_crit, base=base, variance_multiplier=var_mul)
