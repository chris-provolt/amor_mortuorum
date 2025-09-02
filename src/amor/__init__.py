"""Amor Mortuorum package root.

This package contains core game systems such as party management,
combat, and UI HUD utilities. Modules are designed to be testable
and decoupled from rendering frameworks; rendering backends (e.g.,
Arcade) are optional and imported lazily where needed.
"""

__all__ = [
    "core",
    "combat",
    "ui",
]
