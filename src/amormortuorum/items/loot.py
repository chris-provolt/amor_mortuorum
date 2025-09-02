from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

from ..core.rng import RNG


@dataclass(frozen=True)
class LootItem:
    """
    Represents an item in a loot table.

    Attributes:
        name: Identifier for the item (unique within its table for tests).
        min_depth: Lowest dungeon depth at which this item can appear.
        max_depth: Highest dungeon depth at which this item can appear.
        weight: Relative weight for selection among eligible items.
        quality: An integer quality tier (1=common .. higher=better).
        theme: Optional theme string to support themed chests.
    """

    name: str
    min_depth: int = 1
    max_depth: int = 99
    weight: int = 1
    quality: int = 1
    theme: str = "generic"

    def eligible(self, depth: int, theme: Optional[str] = None,
                 min_quality: Optional[int] = None, max_quality: Optional[int] = None) -> bool:
        if depth < self.min_depth or depth > self.max_depth:
            return False
        if theme is not None and self.theme != theme:
            return False
        if min_quality is not None and self.quality < min_quality:
            return False
        if max_quality is not None and self.quality > max_quality:
            return False
        if self.weight <= 0:
            return False
        return True


@dataclass
class LootTable:
    """
    A data-driven loot table supporting depth-gating, themed chests, and
    weighted selection. Designed to be deterministic when provided with an RNG
    seeded instance.
    """

    items: List[LootItem] = field(default_factory=list)

    def add_item(self, item: LootItem) -> None:
        self.items.append(item)

    def extend(self, items: Iterable[LootItem]) -> None:
        self.items.extend(items)

    def _eligible_items(self, depth: int, theme: Optional[str],
                        min_quality: Optional[int], max_quality: Optional[int]) -> List[LootItem]:
        return [i for i in self.items if i.eligible(depth, theme, min_quality, max_quality)]

    def roll(self, depth: int, rng: RNG,
             theme: Optional[str] = None,
             min_quality: Optional[int] = None,
             max_quality: Optional[int] = None) -> LootItem:
        """
        Roll an item from the loot table satisfying provided constraints.

        Raises:
            ValueError if no eligible items exist for the given constraints.
        """
        eligible = self._eligible_items(depth, theme, min_quality, max_quality)
        if not eligible:
            raise ValueError("No eligible items to roll from this loot table")
        total_weight = sum(i.weight for i in eligible)
        # Manual weighted choice to keep RNG API minimal and deterministic
        threshold = rng.uniform(0, total_weight)
        cumulative = 0.0
        for item in eligible:
            cumulative += item.weight
            if threshold <= cumulative:
                return item
        # Fallback for floating point edge: return last element deterministically
        return eligible[-1]

    def roll_n(self, n: int, depth: int, rng: RNG, **kwargs) -> List[LootItem]:
        return [self.roll(depth, rng, **kwargs) for _ in range(n)]

    def __len__(self) -> int:
        return len(self.items)

    def names(self) -> Sequence[str]:
        return [i.name for i in self.items]
