from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .meta_store import MetaStore
from .relics_data import RelicsData
from ..core.events import EventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelicsSnapshot:
    collected_ids: List[str]
    final_collected: bool
    collected_count: int
    total_fragments: int


class RelicsManager:
    """Manages the collection state of Relics of the Veil and persistence to meta.json.

    Emits 'relics:updated' events with a RelicsSnapshot payload when the state changes.
    """

    EVENT_UPDATED = "relics:updated"

    def __init__(self, meta_store: MetaStore, relics_data: RelicsData, event_bus: EventBus) -> None:
        self._store = meta_store
        self._data = relics_data
        self._bus = event_bus
        self._fragment_ids: Set[str] = set()
        self._final_collected: bool = False
        self._load_from_store()

    def _load_from_store(self) -> None:
        data = self._store.load()
        relics = data.get("relics", {})
        collected = set(relics.get("collected_ids", []))
        final_collected = bool(relics.get("final_collected", False))
        # Sanitize: keep only known fragment ids and clamp to 9
        known_fragments = set(self._data.fragment_ids)
        self._fragment_ids = collected & known_fragments
        self._final_collected = final_collected
        if self._fragment_ids != collected or "relics" not in data:
            # Save back sanitized/initialized structure
            logger.info("Sanitizing meta relics section or initializing defaults")
            self._persist()

    def _persist(self) -> None:
        def transform(d: Dict) -> Dict:
            d.setdefault("version", self._store.CURRENT_VERSION)
            d["relics"] = {
                "collected_ids": sorted(self._fragment_ids, key=lambda x: self._data.fragment_ids.index(x)),
                "final_collected": self._final_collected,
            }
            return d

        saved = self._store.update(transform)
        logger.debug("Persisted relics state: %r", saved.get("relics"))

    def _emit(self) -> None:
        snapshot = RelicsSnapshot(
            collected_ids=self.collected_ids(),
            final_collected=self._final_collected,
            collected_count=self.collected_count(),
            total_fragments=self.total_fragments(),
        )
        self._bus.emit(self.EVENT_UPDATED, snapshot)

    # Public API

    def collect_relic(self, relic_id: str) -> bool:
        """Collect a fragment relic by id.

        Returns True if this call added a new relic (state changed), False if it was already collected.
        Raises KeyError if the id is unknown, or ValueError if the id is not a fragment relic.
        """
        relic = self._data.by_id(relic_id)
        if relic.kind != "fragment":
            raise ValueError(f"Relic '{relic_id}' is not a fragment and cannot be collected via collect_relic().")
        if relic_id in self._fragment_ids:
            logger.info("Relic '%s' already collected; ignoring.", relic_id)
            return False
        self._fragment_ids.add(relic_id)
        self._persist()
        self._emit()
        logger.info("Collected relic '%s' (%d/%d)", relic_id, self.collected_count(), self.total_fragments())
        return True

    def collect_final_relic(self) -> bool:
        """Mark the final relic as collected.

        Returns True if state changed; False if already collected.
        """
        if self._final_collected:
            logger.info("Final relic already collected; ignoring.")
            return False
        self._final_collected = True
        self._persist()
        self._emit()
        logger.info("Collected final relic ")
        return True

    def is_collected(self, relic_id: str) -> bool:
        relic = self._data.by_id(relic_id)
        return relic.kind == "fragment" and relic_id in self._fragment_ids

    def collected_ids(self) -> List[str]:
        return sorted(self._fragment_ids, key=lambda x: self._data.fragment_ids.index(x))

    def collected_count(self) -> int:
        return len(self._fragment_ids)

    def total_fragments(self) -> int:
        return len(self._data.fragments)

    def final_collected(self) -> bool:
        return self._final_collected

    def progress(self) -> Tuple[int, int, bool]:
        return self.collected_count(), self.total_fragments(), self._final_collected

    def reset(self) -> None:
        """Reset in-memory and persisted relics state (for tests or debug)."""
        self._fragment_ids.clear()
        self._final_collected = False
        self._persist()
        self._emit()
