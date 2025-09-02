import logging
from dataclasses import dataclass

from amormortuorum.runtime.exceptions import InsufficientFundsError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class Wallet:
    """Simple wallet model for player gold."""

    initial_gold: int = 0

    def __post_init__(self) -> None:
        if self.initial_gold < 0:
            raise ValidationError("Initial gold cannot be negative")
        self._gold = int(self.initial_gold)

    @property
    def gold(self) -> int:
        return self._gold

    def earn(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("Amount to earn cannot be negative")
        self._gold += amount
        logger.debug("Earned %d gold (total: %d)", amount, self._gold)

    def spend(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("Amount to spend cannot be negative")
        if amount > self._gold:
            raise InsufficientFundsError(
                f"Cannot spend {amount} gold; only {self._gold} available."
            )
        self._gold -= amount
        logger.debug("Spent %d gold (remaining: %d)", amount, self._gold)
