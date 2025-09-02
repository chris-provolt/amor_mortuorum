from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from amor_mortuorum.combat.context import Combatant, CombatContext
from amor_mortuorum.combat.item_resolver import ItemResolver


class Action:
    """Base combat action interface."""

    def execute(self, context: CombatContext) -> None:
        raise NotImplementedError


@dataclass
class UseItemAction(Action):
    """
    Action to use an item in combat. Resolves immediately and consumes
    a single quantity of the item.
    """

    actor: Combatant
    item_id: str
    target: Optional[Combatant] = None
    resolver: ItemResolver = ItemResolver()

    def execute(self, context: CombatContext) -> None:
        self.resolver.use_item(context, self.actor, self.item_id, self.target)
