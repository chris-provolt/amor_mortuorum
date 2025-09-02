import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from amor.core.save_service import SaveService

logger = logging.getLogger(__name__)

# Default relic definitions as a fallback (IDs stable for persistence)
DEFAULT_RELIC_DEFINITIONS: List[Dict] = [
    {"id": "veil_fragment_i", "name": "Veil Fragment I", "order": 1, "category": "fragment"},
    {"id": "veil_fragment_ii", "name": "Veil Fragment II", "order": 2, "category": "fragment"},
    {"id": "veil_fragment_iii", "name": "Veil Fragment III", "order": 3, "category": "fragment"},
    {"id": "veil_fragment_iv", "name": "Veil Fragment IV", "order": 4, "category": "fragment"},
    {"id": "veil_fragment_v", "name": "Veil Fragment V", "order": 5, "category": "fragment"},
    {"id": "veil_fragment_vi", "name": "Veil Fragment VI", "order": 6, "category": "fragment"},
    {"id": "veil_fragment_vii", "name": "Veil Fragment VII", "order": 7, "category": "fragment"},
    {"id": "veil_fragment_viii", "name": "Veil Fragment VIII", "order": 8, "category": "fragment"},
    {"id": "veil_fragment_ix", "name": "Veil Fragment IX", "order": 9, "category": "fragment"},
    {"id": "heart_of_oblivion", "name": "Heart of Oblivion", "order": 10, "category": "final", "award_condition": "final_boss_defeat"},
]


@dataclass(frozen=True)
class Relic:
    id: str
    name: str
    order: int
    category: str
    award_condition: Optional[str] = None


class RelicDefinitions:
    """Loads and indexes relic definitions from JSON or built-ins."""

    def __init__(self, json_path: Optional[str] = None) -> None:
        self._defs: Dict[str, Relic] = {}
        self._ordered_ids: List[str] = []
        self._load(json_path)

    def _load(self, json_path: Optional[str]) -> None:
        blobs: List[Dict]
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                    if not isinstance(raw, list):
                        raise ValueError("Relics JSON must be a list of objects")
                    blobs = raw
            except Exception as e:
                logger.error("Failed to load relic definitions from %s: %s", json_path, e)
                blobs = DEFAULT_RELIC_DEFINITIONS
        else:
            # Try repo-level data fallback
            repo_data_path = os.path.join(os.getcwd(), "data", "relics.json")
            if os.path.exists(repo_data_path):
                try:
                    with open(repo_data_path, "r", encoding="utf-8") as fh:
                        raw = json.load(fh)
                        if not isinstance(raw, list):
                            raise ValueError("Relics JSON must be a list of objects")
                        blobs = raw
                except Exception as e:
                    logger.error("Failed to load relic definitions from repo data: %s", e)
                    blobs = DEFAULT_RELIC_DEFINITIONS
            else:
                blobs = DEFAULT_RELIC_DEFINITIONS
        # Build indices
        try:
            items: List[Relic] = []
            for b in blobs:
                items.append(
                    Relic(
                        id=str(b["id"]),
                        name=str(b.get("name", b["id"])),
                        order=int(b.get("order", 0)),
                        category=str(b.get("category", "misc")),
                        award_condition=b.get("award_condition"),
                    )
                )
            items.sort(key=lambda r: r.order)
            self._defs = {r.id: r for r in items}
            self._ordered_ids = [r.id for r in items]
        except Exception as e:
            logger.exception("Invalid relic definitions; falling back to defaults. Error: %s", e)
            self._defs = {d["id"]: Relic(**d) for d in DEFAULT_RELIC_DEFINITIONS}
            self._ordered_ids = [d["id"] for d in DEFAULT_RELIC_DEFINITIONS]

    def get(self, relic_id: str) -> Optional[Relic]:
        return self._defs.get(relic_id)

    def all_ids(self) -> List[str]:
        return list(self._ordered_ids)

    def final_relic_id(self) -> str:
        # Convention: the one with category == 'final' and award_condition == 'final_boss_defeat'
        for rid in self._ordered_ids:
            r = self._defs[rid]
            if r.category == "final" and r.award_condition == "final_boss_defeat":
                return r.id
        # fallback to known id
        return "heart_of_oblivion"


class RelicManager:
    """Tracks collection state and persists via SaveService.

    Persistence schema under section 'relics':
      {
        "version": 1,
        "collected": ["relic_id", ...]
      }
    """

    SECTION = "relics"

    def __init__(self, save: SaveService, defs: Optional[RelicDefinitions] = None) -> None:
        self._save = save
        self._defs = defs or RelicDefinitions()
        self._collected: Set[str] = set()
        self._load()

    def _load(self) -> None:
        sec = self._save.get_section(self.SECTION, default={"version": 1, "collected": []})
        collection = sec.get("collected", [])
        if not isinstance(collection, list):
            logger.warning("Relics section malformed; resetting collection.")
            collection = []
        # Filter to known relic IDs only
        known = set(self._defs.all_ids())
        self._collected = {rid for rid in collection if isinstance(rid, str) and rid in known}
        # Optionally write back cleaned data if it differed
        if set(collection) != self._collected or sec.get("version") != 1:
            self._persist()

    def _persist(self) -> None:
        data = {"version": 1, "collected": sorted(self._collected)}
        self._save.update_section(self.SECTION, data)

    def all_relic_ids(self) -> List[str]:
        return self._defs.all_ids()

    def is_collected(self, relic_id: str) -> bool:
        return relic_id in self._collected

    def collected_count(self) -> int:
        return len(self._collected)

    def award(self, relic_id: str) -> bool:
        """Award a relic if not already collected. Returns True if newly awarded."""
        if relic_id not in set(self._defs.all_ids()):
            logger.error("Attempted to award unknown relic id: %s", relic_id)
            return False
        if relic_id in self._collected:
            logger.debug("Relic %s already collected; not awarding again.", relic_id)
            return False
        self._collected.add(relic_id)
        self._persist()
        logger.info("Awarded relic: %s", relic_id)
        return True

    def award_final_relic(self) -> bool:
        rid = self._defs.final_relic_id()
        return self.award(rid)

    def as_ui_state(self) -> List[Dict[str, object]]:
        """Returns an ordered list of relic state for UI consumption."""
        out: List[Dict[str, object]] = []
        for rid in self._defs.all_ids():
            relic = self._defs.get(rid)
            if relic is None:
                continue
            out.append({
                "id": relic.id,
                "name": relic.name,
                "order": relic.order,
                "category": relic.category,
                "collected": self.is_collected(relic.id),
            })
        return out
