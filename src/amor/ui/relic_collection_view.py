from dataclasses import dataclass
from typing import List

from amor.meta.relics import RelicManager


@dataclass
class RelicItemView:
    id: str
    name: str
    order: int
    category: str
    collected: bool


class RelicCollectionView:
    """Lightweight ViewModel backing the Relics Collection UI.

    In the production app, this would feed the Arcade UI with icons/text states.
    Here, it's a simple struct list suitable for testing.
    """

    def __init__(self, relics: RelicManager) -> None:
        self._relics = relics

    def items(self) -> List[RelicItemView]:
        state = self._relics.as_ui_state()
        return [
            RelicItemView(
                id=e["id"],
                name=e["name"],
                order=e["order"],
                category=e["category"],
                collected=bool(e["collected"]),
            )
            for e in state
        ]

    def is_final_relic_collected(self) -> bool:
        for item in self.items():
            if item.category == "final":
                return item.collected
        return False
