from __future__ import annotations

import logging
from typing import Any, Dict, Callable, Sequence

from amormortuorum.config import KEY_MINIMAP_TOGGLE
from amormortuorum.ui.minimap import Minimap

logger = logging.getLogger(__name__)

try:
    import arcade
except Exception:  # pragma: no cover - optional in tests
    class _ArcadeKey:
        # Minimal stub for key constants used
        M = ord("M")
    arcade = type("arcade", (), {"key": _ArcadeKey})()  # type: ignore


class KeyboardController:
    """
    Receives raw key events (from Arcade's on_key_press or a test harness) and invokes
    the appropriate action handlers.

    This controller centralizes input mapping to support easy rebinding/testing.
    """

    def __init__(self, minimap: Minimap):
        self.minimap = minimap
        self._handlers: Dict[str, Callable[[], Any]] = {
            KEY_MINIMAP_TOGGLE.upper(): self.minimap.toggle,
        }
        # Allow numeric and arcade key codes to access the same action
        self._arcade_code_map: Dict[int, str] = {
            getattr(arcade.key, KEY_MINIMAP_TOGGLE.upper(), arcade.key.M): KEY_MINIMAP_TOGGLE.upper(),
        }

    def handle_key_press(self, symbol: Any, modifiers: int = 0) -> bool:
        """
        Handle a key press event. Accepts Arcade key code (int) or a single-character string.
        Returns True if the event was handled, False otherwise.
        """
        action_key = None
        if isinstance(symbol, int) and symbol in self._arcade_code_map:
            action_key = self._arcade_code_map[symbol]
        elif isinstance(symbol, str) and len(symbol) == 1:
            action_key = symbol.upper()

        if action_key and action_key in self._handlers:
            logger.info("Handling key action: %s", action_key)
            self._handlers[action_key]()
            return True

        logger.debug("Unhandled key: %s (modifiers=%s)", symbol, modifiers)
        return False

    def bind(self, key: str, handler: Callable[[], Any]) -> None:
        """Bind an additional single-character key to a handler."""
        if not key or len(key) != 1:
            raise ValueError("Key must be a single character string")
        self._handlers[key.upper()] = handler

    def unbind(self, key: str) -> None:
        if not key or len(key) != 1:
            raise ValueError("Key must be a single character string")
        self._handlers.pop(key.upper(), None)
