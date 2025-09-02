import logging
from dataclasses import dataclass
from typing import Optional

from .events import EventBus, GoldChangedEvent

logger = logging.getLogger(__name__)


@dataclass
class GoldWallet:
    """Represents the player's gold wallet.

    Emits GoldChangedEvent on every state change via provided EventBus.
    """

    event_bus: EventBus
    _amount: int = 0
    max_gold: Optional[int] = None

    @property
    def amount(self) -> int:
        return self._amount

    def can_afford(self, cost: int) -> bool:
        if cost < 0:
            return False
        return self._amount >= cost

    def add(self, amount: int, reason: str = "adjust") -> int:
        if amount < 0:
            raise ValueError("Cannot add negative gold; use spend() for deduction")
        old = self._amount
        new = old + amount
        if self.max_gold is not None:
            new = min(new, self.max_gold)
        self._amount = new
        delta = new - old
        logger.debug("Gold added: +%s (reason=%s); old=%s new=%s", delta, reason, old, new)
        self.event_bus.emit(GoldChangedEvent(old_amount=old, new_amount=new, delta=delta, reason=reason))
        return delta

    def spend(self, amount: int, reason: str = "purchase") -> int:
        if amount < 0:
            raise ValueError("Cannot spend negative gold")
        if amount == 0:
            return 0
        if not self.can_afford(amount):
            raise ValueError(f"Insufficient gold: have {self._amount}, need {amount}")
        old = self._amount
        new = old - amount
        self._amount = new
        logger.debug("Gold spent: -%s (reason=%s); old=%s new=%s", amount, reason, old, new)
        self.event_bus.emit(GoldChangedEvent(old_amount=old, new_amount=new, delta=new - old, reason=reason))
        return amount

    def set(self, amount: int, reason: str = "adjust") -> None:
        if amount < 0:
            raise ValueError("Gold cannot be negative")
        if self.max_gold is not None:
            amount = min(amount, self.max_gold)
        old = self._amount
        self._amount = amount
        if old != amount:
            logger.debug("Gold set: old=%s new=%s (reason=%s)", old, amount, reason)
            self.event_bus.emit(GoldChangedEvent(old_amount=old, new_amount=amount, delta=amount - old, reason=reason))
