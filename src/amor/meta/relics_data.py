from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Relic:
    """Immutable data for a Relic definition.

    Attributes:
        id: Unique identifier, e.g., 'veil_fragment_1' or 'veil_final'.
        name: Display name.
        description: Flavor text.
        kind: 'fragment' or 'final'.
        order: Order of the fragment (1..9) for fragments; None for final.
        icon: Optional icon path reference (not used in tests but reserved for UI).
    """

    id: str
    name: str
    description: str
    kind: str  # 'fragment' | 'final'
    order: Optional[int] = None
    icon: Optional[str] = None


class RelicsData:
    """Loads and validates relics definitions from a JSON data file.

    Expects exactly 9 fragments and 1 final relic.
    """

    def __init__(self, relics: List[Relic]) -> None:
        self._relics = relics
        self._validate()
        self._by_id: Dict[str, Relic] = {r.id: r for r in relics}
        self._fragments_sorted: List[Relic] = sorted(
            [r for r in relics if r.kind == "fragment"], key=lambda r: r.order or 0
        )
        self._final: Relic = next(r for r in relics if r.kind == "final")

    def _validate(self) -> None:
        fragments = [r for r in self._relics if r.kind == "fragment"]
        finals = [r for r in self._relics if r.kind == "final"]
        if len(fragments) != 9:
            raise ValueError(f"Expected 9 fragment relics, found {len(fragments)}")
        if len(finals) != 1:
            raise ValueError(f"Expected 1 final relic, found {len(finals)}")
        orders = [r.order for r in fragments]
        if any(o is None for o in orders):
            raise ValueError("All fragment relics must have an 'order' field")
        if sorted(orders) != list(range(1, 10)):
            raise ValueError("Fragment 'order' values must be 1..9 without gaps")
        ids = [r.id for r in self._relics]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate relic ids found in data")

    @classmethod
    def from_file(cls, path: Path | str) -> "RelicsData":
        path = Path(path)
        logger.debug("Loading relics data from %s", path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        relics: List[Relic] = []
        for entry in raw:
            relics.append(
                Relic(
                    id=entry["id"],
                    name=entry["name"],
                    description=entry.get("description", ""),
                    kind=entry["kind"],
                    order=entry.get("order"),
                    icon=entry.get("icon"),
                )
            )
        return cls(relics)

    @property
    def all(self) -> List[Relic]:
        return list(self._relics)

    @property
    def fragments(self) -> List[Relic]:
        return list(self._fragments_sorted)

    @property
    def fragment_ids(self) -> List[str]:
        return [r.id for r in self._fragments_sorted]

    @property
    def final(self) -> Relic:
        return self._final

    def by_id(self, relic_id: str) -> Relic:
        try:
            return self._by_id[relic_id]
        except KeyError:
            raise KeyError(f"Unknown relic id: {relic_id}")
