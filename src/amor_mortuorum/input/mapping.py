from __future__ import annotations

import logging
from typing import Dict, Iterable, Optional

from .actions import InputAction, InputEvent

logger = logging.getLogger(__name__)


class InputMapper:
    """Rebindable mapping from physical keys/buttons to logical actions.

    The mapper is agnostic to the input backend. Keys are represented as strings
    that are normalized internally (case-insensitive). This enables easy
    integration with various frameworks (Arcade, Pyglet, SDL, etc.) by simply
    translating their key constants to canonical string names before passing
    them to this mapper.

    Example usage:
        mapper = InputMapper.default()
        action = mapper.translate_key("w")   # -> InputAction.MOVE_UP
        evt = mapper.on_key_event("ENTER", pressed=True)
    """

    def __init__(self, bindings: Optional[Dict[str, InputAction]] = None) -> None:
        # Internal storage uses canonical uppercase string keys
        self._bindings: Dict[str, InputAction] = {}
        if bindings:
            for key, action in bindings.items():
                self.bind(key, action)

        # Optional alias table mapping input backend specific keys (strings or ints)
        # to canonical key strings. Users/integrations can extend this.
        self._aliases: Dict[str, str] = {}

    # ---------- Canonicalization ----------
    @staticmethod
    def _normalize(key: str | int) -> Optional[str]:
        """Normalize a key into a canonical uppercase string.

        Accepts ints or strings; ints are converted to strings. Returns None
        for unsupported/empty inputs.
        """
        if key is None:
            return None
        if isinstance(key, int):
            # Convert numeric codes to a string name (caller should set aliases as needed)
            return str(key)
        if not isinstance(key, str):
            return None
        k = key.strip()
        if not k:
            return None
        return k.upper()

    # ---------- Binding API ----------
    def bind(self, key: str | int, action: InputAction) -> None:
        """Bind a single key to an action."""
        nk = self._normalize(key)
        if nk is None:
            logger.warning("Attempted to bind invalid key: %r", key)
            return
        self._bindings[nk] = action

    def bind_many(self, keys: Iterable[str | int], action: InputAction) -> None:
        """Bind multiple keys to the same action."""
        for k in keys:
            self.bind(k, action)

    def unbind(self, key: str | int) -> None:
        nk = self._normalize(key)
        if nk is not None:
            self._bindings.pop(nk, None)

    def set_alias(self, physical: str | int, canonical_name: str) -> None:
        """Register an alias mapping from a backend-specific key to a canonical name.

        Example: set_alias(65362, "UP") or set_alias("RETURN", "ENTER").
        """
        nk = self._normalize(physical)
        cn = self._normalize(canonical_name)
        if nk and cn:
            self._aliases[nk] = cn

    # ---------- Translation ----------
    def translate_key(self, key: str | int) -> Optional[InputAction]:
        """Translate a physical key into a logical action or None.

        Applies alias remapping, then looks up the action in the binding table.
        """
        nk = self._normalize(key)
        if nk is None:
            return None
        # Apply alias if present (may chain one level)
        canonical = self._aliases.get(nk, nk)
        return self._bindings.get(canonical)

    def on_key_event(self, key: str | int, pressed: bool, source: str = "keyboard") -> Optional[InputEvent]:
        """Convenience helper to produce an InputEvent from a key press/release.

        Returns None if the key is not bound to any action.
        """
        action = self.translate_key(key)
        if action is None:
            return None
        return InputEvent(action=action, pressed=pressed, source=source)

    # ---------- Defaults ----------
    @classmethod
    def default(cls) -> "InputMapper":
        """Create a default mapper with Arrow/WASD, Enter/Return, Escape mapped uniformly.

        - Arrows and WASD map to MOVE actions.
        - Enter/Return map to CONFIRM.
        - Escape/ESC map to BACK.
        """
        mapper = cls()

        # Movement: Arrows
        mapper.bind_many(["UP"], InputAction.MOVE_UP)
        mapper.bind_many(["DOWN"], InputAction.MOVE_DOWN)
        mapper.bind_many(["LEFT"], InputAction.MOVE_LEFT)
        mapper.bind_many(["RIGHT"], InputAction.MOVE_RIGHT)

        # Movement: WASD
        mapper.bind_many(["W"], InputAction.MOVE_UP)
        mapper.bind_many(["S"], InputAction.MOVE_DOWN)
        mapper.bind_many(["A"], InputAction.MOVE_LEFT)
        mapper.bind_many(["D"], InputAction.MOVE_RIGHT)

        # Confirm: Enter / Return (and common synonyms)
        mapper.bind_many(["ENTER", "RETURN", "NUM_ENTER"], InputAction.CONFIRM)
        # Alias some common variants to ENTER
        mapper.set_alias("RET", "ENTER")

        # Back: Escape (and synonyms)
        mapper.bind_many(["ESCAPE", "ESC"], InputAction.BACK)

        return mapper


__all__ = ["InputMapper"]
