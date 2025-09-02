from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class PlayerStats:
    """
    Observable player stats model.

    Provides listener binding so UI components (HUD) can update live when values change.
    """

    max_hp: int = 100
    hp: int = 100
    max_mp: int = 30
    mp: int = 30
    gold: int = 0

    _listeners: List[Callable[[str, Dict[str, Any]], None]] = field(default_factory=list, init=False, repr=False)

    def add_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)
            logger.debug("Listener added to PlayerStats: %s", callback)

    def remove_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
            logger.debug("Listener removed from PlayerStats: %s", callback)

    # --- Internal notification helpers ---
    def _notify(self, event: str, payload: Dict[str, Any]) -> None:
        for cb in list(self._listeners):  # copy in case listeners mutate during notify
            try:
                cb(event, payload)
            except Exception as exc:
                logger.exception("Listener error for event '%s': %s", event, exc)

    # --- HP / MP management ---
    def set_hp(self, value: int) -> int:
        old = self.hp
        self.hp = max(0, min(self.max_hp, int(value)))
        if self.hp != old:
            logger.info("HP changed: %s -> %s", old, self.hp)
            self._notify("hp", {"hp": self.hp, "max_hp": self.max_hp})
        return self.hp

    def change_hp(self, delta: int) -> int:
        return self.set_hp(self.hp + int(delta))

    def set_mp(self, value: int) -> int:
        old = self.mp
        self.mp = max(0, min(self.max_mp, int(value)))
        if self.mp != old:
            logger.info("MP changed: %s -> %s", old, self.mp)
            self._notify("mp", {"mp": self.mp, "max_mp": self.max_mp})
        return self.mp

    def change_mp(self, delta: int) -> int:
        return self.set_mp(self.mp + int(delta))

    # --- Gold management ---
    def set_gold(self, value: int) -> int:
        old = self.gold
        self.gold = max(0, int(value))
        if self.gold != old:
            logger.info("Gold changed: %s -> %s", old, self.gold)
            self._notify("gold", {"gold": self.gold})
        return self.gold

    def add_gold(self, amount: int) -> int:
        return self.set_gold(self.gold + int(amount))

    def spend_gold(self, amount: int) -> int:
        if amount < 0:
            logger.warning("Attempted to spend negative gold: %s", amount)
            return self.gold
        if amount > self.gold:
            logger.warning("Attempted to overspend gold: have=%s, need=%s", self.gold, amount)
            # Clamp to 0 (spend all) or reject? Choose reject for safety.
            return self.gold
        return self.set_gold(self.gold - int(amount))
