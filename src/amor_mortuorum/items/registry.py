from __future__ import annotations

from typing import Dict

from .effects import HealHP, RestoreMP, Damage
from .models import ItemDefinition


class ItemRegistry:
    """
    In-memory registry of item definitions used in combat.

    This implementation hardcodes a small set of items suitable for tests and
    initial gameplay. It can be extended to load from data files.
    """

    def __init__(self) -> None:
        self._defs: Dict[str, ItemDefinition] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        # Potions
        self.register(
            ItemDefinition(
                id="potion_hp_small",
                name="Minor Healing Potion",
                kind="potion",
                target="ally_or_self",
                effects=[HealHP(50)],
            )
        )
        self.register(
            ItemDefinition(
                id="potion_mp_small",
                name="Minor Ether",
                kind="potion",
                target="ally_or_self",
                effects=[RestoreMP(30)],
            )
        )
        # Scrolls
        self.register(
            ItemDefinition(
                id="scroll_fire",
                name="Scroll of Fire",
                kind="scroll",
                target="enemy",
                effects=[Damage(40, element="fire")],
            )
        )
        self.register(
            ItemDefinition(
                id="scroll_heal",
                name="Scroll of Mend",
                kind="scroll",
                target="ally_or_self",
                effects=[HealHP(40)],
            )
        )

    def register(self, definition: ItemDefinition) -> None:
        self._defs[definition.id] = definition

    def get(self, item_id: str) -> ItemDefinition:
        try:
            return self._defs[item_id]
        except KeyError as exc:
            raise KeyError(f"Unknown item id: {item_id}") from exc


# A default, module-level registry for convenience
DEFAULT_ITEM_REGISTRY = ItemRegistry()
