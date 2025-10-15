from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Set

import arcade

logger = logging.getLogger(__name__)


# Default logical actions used across the game
DEFAULT_ACTIONS = {
    "move_up",
    "move_down",
    "move_left",
    "move_right",
    "confirm",
    "cancel",
    "menu",
    "pause",
    "debug",
}


def _normalize_key_name(name: str) -> int:
    """Translate a human-friendly key name to an arcade.key constant.

    Accepts either:
    - Exact constant names (e.g., "UP", "ENTER")
    - Single characters (e.g., "w", "A") which map to arcade.key.W/arcade.key.A
    """
    if len(name) == 1:
        name = name.upper()
    try:
        return getattr(arcade.key, name)
    except AttributeError as e:
        raise ValueError(f"Unknown key name: {name}") from e


class InputManager:
    """
    Action-based input mapping and translation layer.

    - Maintains mapping from logical actions -> set of arcade key codes
    - Provides helper methods to translate key events to action names
    - Can be extended to support gamepad, axes, and chords
    """

    def __init__(
        self,
        window: arcade.Window,
        mapping: Dict[str, Iterable[str]] | None = None,
    ) -> None:
        self.window = window
        self._mapping: Dict[str, Set[int]] = {}
        self._pressed: Set[int] = set()

        if not mapping:
            mapping = self._default_mapping()
        self._apply_mapping(mapping)
        logger.debug("Input mapping initialized: %s", self._mapping)

    def _apply_mapping(self, mapping: Dict[str, Iterable[str]]):
        for action, key_names in mapping.items():
            keys = {_normalize_key_name(name) for name in key_names}
            self._mapping[action] = keys

    @staticmethod
    def _default_mapping() -> Dict[str, Iterable[str]]:
        return {
            "move_up": ["W", "UP"],
            "move_down": ["S", "DOWN"],
            "move_left": ["A", "LEFT"],
            "move_right": ["D", "RIGHT"],
            "confirm": ["ENTER", "SPACE"],
            "cancel": ["ESCAPE", "BACKSPACE"],
            "menu": ["TAB"],
            "pause": ["P"],
            "debug": ["F3"],
        }

    # Query helpers
    def actions_for_key(self, key: int) -> List[str]:
        actions = [action for action, keys in self._mapping.items() if key in keys]
        logger.debug("Key %s maps to actions %s", key, actions)
        return actions

    # Event processing
    def process_key_press(self, key: int, modifiers: int) -> List[str]:
        self._pressed.add(key)
        actions = self.actions_for_key(key)
        logger.debug("Key pressed %s mods=%s actions=%s", key, modifiers, actions)
        return actions

    def process_key_release(self, key: int, modifiers: int) -> List[str]:
        self._pressed.discard(key)
        actions = self.actions_for_key(key)
        logger.debug("Key released %s mods=%s actions=%s", key, modifiers, actions)
        return actions

    # Binding management
    def bind(self, action: str, keys: Iterable[str]) -> None:
        self._mapping[action] = {_normalize_key_name(k) for k in keys}
        logger.info("Bound action '%s' to keys %s", action, keys)

    def unbind(self, action: str) -> None:
        if action in self._mapping:
            del self._mapping[action]
            logger.info("Unbound action '%s'", action)

    def is_pressed(self, action: str) -> bool:
        keys = self._mapping.get(action, set())
        return any(k in self._pressed for k in keys)
