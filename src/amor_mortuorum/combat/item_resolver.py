from __future__ import annotations

from typing import Optional

from amor_mortuorum.exceptions import InventoryError, ItemUseError
from amor_mortuorum.items.models import ItemDefinition
from amor_mortuorum.items.registry import DEFAULT_ITEM_REGISTRY, ItemRegistry
from .context import CombatContext, Combatant


class ItemResolver:
    """
    Resolves item usage during combat: validates targets, applies effects,
    logs results, and consumes the item from the actor's inventory.
    """

    def __init__(self, registry: Optional[ItemRegistry] = None) -> None:
        self.registry = registry or DEFAULT_ITEM_REGISTRY

    def use_item(
        self,
        context: CombatContext,
        actor: Combatant,
        item_id: str,
        target: Optional[Combatant] = None,
    ) -> None:
        """
        Use an item in combat. Resolves immediately. Consumes a single quantity.

        - Potions restore HP/MP on allies or self (default to self).
        - Scrolls cast simple spells (damage enemy, or heal an ally).
        """
        # Check inventory
        if not actor.inventory.has(item_id):
            raise ItemUseError(
                f"{actor.name} does not have item '{item_id}' to use."
            )

        # Get item definition
        try:
            definition: ItemDefinition = self.registry.get(item_id)
        except KeyError as exc:
            raise ItemUseError(str(exc)) from exc

        # Resolve target
        resolved_target = self._resolve_target(context, actor, definition, target)

        # Apply effects
        context.add_log(f"{actor.name} uses {definition.name}!")
        for effect in definition.effects:
            entry = effect.apply(context, actor, resolved_target)
            context.add_log(entry)

        # Consume item
        try:
            actor.inventory.consume(item_id, 1)
        except InventoryError as exc:
            # This should be rare given earlier check, but guard for race/consistency
            raise ItemUseError(str(exc)) from exc

    def _resolve_target(
        self,
        context: CombatContext,
        actor: Combatant,
        definition: ItemDefinition,
        explicit: Optional[Combatant],
    ) -> Combatant:
        """Validate and pick the actual target based on item definition."""
        target_kind = definition.target

        if target_kind == "self":
            return actor

        if target_kind == "ally_or_self":
            # Default to self if no target provided
            tgt = explicit or actor
            if tgt not in context.allies_of(actor):
                raise ItemUseError(
                    f"Target {tgt.name} is not an ally for item {definition.name}."
                )
            if not tgt.is_alive:
                raise ItemUseError("Cannot target a fallen ally.")
            return tgt

        if target_kind == "ally":
            if explicit is None:
                raise ItemUseError("This item requires an ally target.")
            if explicit not in context.allies_of(actor) or explicit is actor:
                raise ItemUseError("Target must be a different ally.")
            if not explicit.is_alive:
                raise ItemUseError("Cannot target a fallen ally.")
            return explicit

        if target_kind == "enemy":
            if explicit is None:
                raise ItemUseError("This item requires an enemy target.")
            if explicit not in context.enemies_of(actor):
                raise ItemUseError("Target must be an enemy.")
            if not explicit.is_alive:
                raise ItemUseError("Cannot target a defeated enemy.")
            return explicit

        raise ItemUseError(f"Unsupported target kind: {target_kind}")
