from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from amor_mortuorum.utils.math import clamp


class Effect:
    """Base class for item or spell effects."""

    def apply(self, context, actor, target) -> str:  # noqa: ANN001
        raise NotImplementedError


@dataclass
class HealHP(Effect):
    amount: int

    def apply(self, context, actor, target) -> str:  # noqa: ANN001
        before = target.hp
        healed = target.heal_hp(self.amount)
        return f"{target.name} recovers {healed} HP ({before}->{target.hp})."


@dataclass
class RestoreMP(Effect):
    amount: int

    def apply(self, context, actor, target) -> str:  # noqa: ANN001
        before = target.mp
        restored = target.restore_mp(self.amount)
        return f"{target.name} recovers {restored} MP ({before}->{target.mp})."


@dataclass
class Damage(Effect):
    amount: int
    element: Optional[str] = None  # Placeholder for future elemental system

    def apply(self, context, actor, target) -> str:  # noqa: ANN001
        before = target.hp
        dealt = target.take_damage(self.amount)
        if self.element:
            return (
                f"{target.name} takes {dealt} {self.element} damage ({before}->{target.hp})."
            )
        return f"{target.name} takes {dealt} damage ({before}->{target.hp})."
