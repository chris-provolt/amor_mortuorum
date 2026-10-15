"""Party management: recruiting companions and shared-bag conventions.

Conventions used across the game:
- ``run.party[0]`` is the leader; the leader's inventory is the party's shared bag
  and the leader's gold is the party's gold.
- Every member has their own equipment and stats.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from ..data import CompanionDef, GameData
from ..errors import InsufficientGold, InvalidOperation
from .entities import Inventory, Player, Stats
from .progression import sync_level
from .run import Run

logger = logging.getLogger(__name__)

MAX_PARTY = 4


def bag(run: Run) -> Inventory:
    return run.leader.inventory


def in_party(run: Run, companion_id: str) -> bool:
    return any(p.companion_id == companion_id for p in run.party)


def available_companions(run: Run, data: GameData) -> List[CompanionDef]:
    return [c for c in data.companions.values() if not in_party(run, c.id)]


def make_companion(template: CompanionDef, level_xp: int, data: GameData) -> Player:
    """Build a companion from its template, levelled to match ``level_xp``."""
    st = template.stats
    stats = Stats(
        max_hp=st["max_hp"], hp=st["max_hp"], max_mp=st["max_mp"], mp=st["max_mp"],
        atk=st["atk"], df=st["df"], spd=st["spd"],
    )
    member = Player(name=template.name, stats=stats, gold=0, companion_id=template.id)
    member.xp = level_xp
    sync_level(member, data)
    member.heal_full()
    return member


def recruit(run: Run, companion_id: str, data: GameData) -> Player:
    """Pay the leader's gold and add the companion to the party."""
    if len(run.party) >= MAX_PARTY:
        raise InvalidOperation(f"The party is full ({MAX_PARTY} members)")
    if in_party(run, companion_id):
        raise InvalidOperation("That companion already travels with you")
    template = data.companion(companion_id)
    leader = run.leader
    if leader.gold < template.cost:
        raise InsufficientGold(f"{template.name} asks {template.cost} gold; you have {leader.gold}")
    leader.spend_gold(template.cost)
    member = make_companion(template, leader.xp, data)
    member.bonuses = dict(leader.bonuses)
    run.party.append(member)
    logger.info("%s joins the party (%d/%d)", member.name, len(run.party), MAX_PARTY)
    return member


def dismiss(run: Run, index: int) -> Player:
    """Remove a companion (never the leader). Their equipment returns to the bag if it fits."""
    if index <= 0 or index >= len(run.party):
        raise InvalidOperation("Only companions can be dismissed")
    member = run.party.pop(index)
    logger.info("%s leaves the party", member.name)
    return member


def most_wounded(players: List[Player]) -> Optional[int]:
    """Index of the living member with the lowest HP fraction, or None."""
    best: Optional[int] = None
    best_frac = 2.0
    for i, p in enumerate(players):
        if not p.is_alive:
            continue
        frac = p.hp / max(1, p.max_hp)
        if frac < best_frac:
            best, best_frac = i, frac
    return best


__all__ = [
    "MAX_PARTY",
    "bag",
    "available_companions",
    "make_companion",
    "recruit",
    "dismiss",
    "most_wounded",
]
