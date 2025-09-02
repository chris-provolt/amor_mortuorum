from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence, Union
import logging

from .stats import Stats

logger = logging.getLogger(__name__)


@dataclass(eq=True, frozen=True)
class PartyMember:
    """A player-controlled party member.

    Attributes:
        name: The display name of the member.
        stats: The member's stats.
        id: An optional unique identifier for save/lookup.
    """

    name: str
    stats: Stats
    id: Optional[str] = None

    @property
    def is_alive(self) -> bool:
        return self.stats.is_alive


@dataclass
class PartySlotView:
    """A lightweight view of a party slot for HUD rendering.

    This view is immutable snapshot data; modify the PartyMember/Stats to change state.
    """

    index: int
    is_empty: bool
    name: str = ""
    hp: int = 0
    max_hp: int = 0
    mp: int = 0
    max_mp: int = 0
    is_dead: bool = False


class Party:
    """Represents the player's party, supporting up to 4 members.

    Empty slots are permitted and preserved for HUD layout. Iteration yields only
    present (non-empty) members by default.
    """

    MAX_SIZE = 4

    def __init__(self, members: Optional[Sequence[Optional[PartyMember]]] = None) -> None:
        # Internal fixed-size slot list of length 4 holding Optional[PartyMember]
        self._slots: List[Optional[PartyMember]] = [None] * self.MAX_SIZE
        if members:
            if len(members) > self.MAX_SIZE:
                raise ValueError("Party cannot exceed 4 members")
            for i, m in enumerate(members):
                if m is not None and not isinstance(m, PartyMember):
                    raise TypeError("members must be PartyMember or None")
                self._slots[i] = m
        logger.debug("Party initialized with slots: %s", self._slots)

    def __len__(self) -> int:  # number of present members
        return sum(1 for m in self._slots if m is not None)

    def __iter__(self) -> Iterator[PartyMember]:
        return (m for m in self._slots if m is not None)

    @property
    def slots(self) -> Sequence[Optional[PartyMember]]:
        """Return a copy of the slot array (length 4)."""
        return tuple(self._slots)

    def get_slot(self, index: int) -> Optional[PartyMember]:
        self._validate_index(index)
        return self._slots[index]

    def add_member(self, member: PartyMember, slot: Optional[int] = None) -> int:
        """Add a member to the party.

        Args:
            member: The PartyMember to add.
            slot: Optional explicit slot index (0-3). If None, use first empty.
        Returns:
            The slot index where the member was placed.
        Raises:
            ValueError if party is full or slot is occupied; TypeError on invalid member.
        """
        if not isinstance(member, PartyMember):
            raise TypeError("member must be PartyMember")
        if member in self._slots:
            raise ValueError("member already in party")
        if slot is not None:
            self._validate_index(slot)
            if self._slots[slot] is not None:
                raise ValueError(f"slot {slot} already occupied")
            self._slots[slot] = member
            logger.info("Added member '%s' to slot %d", member.name, slot)
            return slot
        # place in first empty
        for i in range(self.MAX_SIZE):
            if self._slots[i] is None:
                self._slots[i] = member
                logger.info("Added member '%s' to slot %d", member.name, i)
                return i
        raise ValueError("party is full")

    def remove_member(self, member_or_index: Union[int, PartyMember]) -> int:
        """Remove a member by index or instance. Returns freed slot index.
        Raises IndexError or ValueError if not found.
        """
        if isinstance(member_or_index, int):
            self._validate_index(member_or_index)
            if self._slots[member_or_index] is None:
                raise ValueError(f"slot {member_or_index} already empty")
            removed = self._slots[member_or_index]
            self._slots[member_or_index] = None
            logger.info("Removed member '%s' from slot %d", removed.name if removed else "?", member_or_index)
            return member_or_index
        # remove by instance
        try:
            idx = self._slots.index(member_or_index)
        except ValueError as e:
            raise ValueError("member not in party") from e
        self._slots[idx] = None
        logger.info("Removed member '%s' from slot %d", member_or_index.name, idx)
        return idx

    def iter_all_members(self) -> Iterator[PartyMember]:
        """Iterate all present members (non-empty slots), regardless of alive state."""
        for m in self._slots:
            if m is not None:
                yield m

    def iter_active_members(self) -> Iterator[PartyMember]:
        """Iterate present and alive members."""
        for m in self._slots:
            if m is not None and m.is_alive:
                yield m

    def as_slot_views(self) -> List[PartySlotView]:
        """Build a HUD-friendly snapshot of 4 slots (empty slots included)."""
        views: List[PartySlotView] = []
        for i, m in enumerate(self._slots):
            if m is None:
                views.append(
                    PartySlotView(index=i, is_empty=True)
                )
            else:
                s = m.stats
                views.append(
                    PartySlotView(
                        index=i,
                        is_empty=False,
                        name=m.name,
                        hp=s.hp,
                        max_hp=s.max_hp,
                        mp=s.mp,
                        max_mp=s.max_mp,
                        is_dead=not s.is_alive,
                    )
                )
        return views

    def _validate_index(self, index: int) -> None:
        if not (0 <= index < self.MAX_SIZE):
            raise IndexError("slot index out of range")
