from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Character:
    """Represents a party member with basic combat resources.

    This is intentionally minimal and self-contained to be usable in tests and
    to integrate into a larger game model. If the main project already has
    richer models, this class can be adapted or mapped accordingly.
    """

    name: str
    max_hp: int
    max_mp: int
    hp: int
    mp: int

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            raise ValueError("max_hp must be positive")
        if self.max_mp < 0:
            raise ValueError("max_mp must be non-negative")
        # Clamp current values into bounds
        self.hp = max(0, min(self.hp, self.max_hp))
        self.mp = max(0, min(self.mp, self.max_mp))

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def heal_full(self) -> None:
        """Restore HP/MP to max without changing alive/dead state.

        If the character is at 0 HP (downed), this will set resources to max.
        Use with caution if your design distinguishes revive from heal; in such
        cases, prefer `revive_and_heal_full` instead for clarity.
        """
        logger.debug("Healing %s to full: HP %s->%s, MP %s->%s", self.name, self.hp, self.max_hp, self.mp, self.max_mp)
        self.hp = self.max_hp
        self.mp = self.max_mp

    def revive_and_heal_full(self) -> None:
        """Revive (if downed) and restore to full HP/MP."""
        was_downed = not self.is_alive
        logger.debug("Reviving %s (downed=%s) and healing to full.", self.name, was_downed)
        self.heal_full()


@dataclass
class Party:
    """Represents the player's party.

    Provides utilities for bulk operations such as full rest at the Graveyard.
    """

    members: List[Character] = field(default_factory=list)

    def restore_all(self, revive_downed: bool = True) -> tuple[int, int]:
        """Restore HP/MP of all party members to full.

        Args:
            revive_downed: If True, downed members (hp == 0) will be revived
                and healed to full. If False, they will remain at 0 HP but MP
                will be restored to max (if your design allows it). Defaults to True.

        Returns:
            Tuple of (healed_members, revived_members).
        """
        healed = 0
        revived = 0

        for member in self.members:
            was_alive = member.is_alive
            if revive_downed and not was_alive:
                member.revive_and_heal_full()
                revived += 1
                healed += 1
            else:
                # Heal to full but do not change alive state if revive is disabled
                before_hp, before_mp = member.hp, member.mp
                member.heal_full()
                if member.hp != before_hp or member.mp != before_mp:
                    healed += 1

            logger.debug(
                "Restored member %s -> HP:%d/%d MP:%d/%d (revived=%s)",
                member.name,
                member.hp,
                member.max_hp,
                member.mp,
                member.max_mp,
                (not was_alive and member.is_alive),
            )

        logger.info("Party restored: healed=%d revived=%d", healed, revived)
        return healed, revived
