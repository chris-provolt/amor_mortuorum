"""
Input abstraction layer for Amor Mortuorum.

Exposes:
- InputAction: Logical input actions used by the game.
- InputEvent: A press/release event for a logical action.
- InputMapper: Rebindable mapping from physical keys to actions.
- GameController: Stub implementation for future controller support.
"""
from .actions import InputAction, InputEvent
from .mapping import InputMapper
from .controllers.controller import GameController

__all__ = [
    "InputAction",
    "InputEvent",
    "InputMapper",
    "GameController",
]
