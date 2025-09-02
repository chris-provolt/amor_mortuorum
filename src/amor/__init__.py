"""
Amor Mortuorum - Core package root

This package provides foundational systems for the game such as events, relics (meta progression),
and stat modifiers. This subset implements Relic passives (light bonuses) with global effects
that can be toggled on/off when owned, and broadcasts changes via a simple event bus.
"""

__all__ = [
    "events",
    "relics",
    "stats",
]
