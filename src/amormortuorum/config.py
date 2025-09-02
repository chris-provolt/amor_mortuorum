from __future__ import annotations

"""
Configuration and policies for gameplay behavior.

For now, we keep it minimal and entirely in Python (no external config files) to
keep tests deterministic and the module self-contained.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResurrectionPolicy:
    """Policy controlling HP and side-effects of resurrection."""

    # Options: "one", "half", "full"
    hp_policy: str = "one"

    def compute_revive_hp(self, max_hp: int) -> int:
        """Compute HP on revival based on policy.

        - one: revive with 1 HP
        - half: revive with ceil(max_hp/2)
        - full: revive with max_hp
        """
        if max_hp <= 0:
            return 1
        if self.hp_policy == "full":
            return max_hp
        if self.hp_policy == "half":
            return max(1, (max_hp + 1) // 2)
        # default: one
        return 1


# Global gameplay policy instance. If needed, may be replaced in tests.
RESURRECTION_POLICY = ResurrectionPolicy(hp_policy="one")

# Naming of the hub location (Graveyard) to avoid string typos across modules.
GRAVEYARD_LOCATION_NAME = "Graveyard"
