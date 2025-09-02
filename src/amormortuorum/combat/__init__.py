"""
Combat package for Amor Mortuorum.

Contains:
- Damage calculation logic with RNG variance and a strict floor of 1 damage.
- Combat entities and basic attack application.
- Combat logging to track attacks and defeats.
"""

from .damage import DamageCalculator
from .entities import Combatant
from .engine import CombatEngine, AttackResult
from .log import CombatLog, CombatEvent

__all__ = [
    "DamageCalculator",
    "Combatant",
    "CombatEngine",
    "AttackResult",
    "CombatLog",
    "CombatEvent",
]
