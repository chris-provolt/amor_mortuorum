from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .errors import SaveValidationError

# Increment when making breaking schema changes
SCHEMA_VERSION = 1

# Canonical set of relic identifiers (9 + 1 as per design; matches data/relics.json)
DEFAULT_RELIC_IDS: Set[str] = {f"veil_{i}" for i in range(1, 10)} | {"veil_final"}


@dataclass
class Item:
    """A persistable description of an item.

    Only minimal fields needed for Crypt persistence are modeled.
    Game runtime may have richer item data referenced by id.
    """

    id: str
    name: str = ""
    qty: int = 1

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise SaveValidationError("Item.id must be a non-empty string")
        if not isinstance(self.name, str):
            raise SaveValidationError("Item.name must be a string")
        if not isinstance(self.qty, int) or self.qty < 1:
            raise SaveValidationError("Item.qty must be a positive integer")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "qty": self.qty}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Item":
        return Item(id=data["id"], name=data.get("name", ""), qty=int(data.get("qty", 1)))


@dataclass
class Crypt:
    """Persistent bank with a fixed number of slots between runs."""

    items: List[Item] = field(default_factory=list)
    MAX_SLOTS: int = 3

    def __post_init__(self) -> None:
        # Ensure no more than MAX_SLOTS items are stored
        if len(self.items) > self.MAX_SLOTS:
            raise SaveValidationError(f"Crypt can hold at most {self.MAX_SLOTS} items")

    def add_item(self, item: Item) -> None:
        if len(self.items) >= self.MAX_SLOTS:
            raise SaveValidationError(
                f"Crypt is full ({self.MAX_SLOTS} slots). Remove an item before adding."
            )
        self.items.append(item)

    def remove_item(self, index: int) -> Item:
        try:
            return self.items.pop(index)
        except IndexError as e:
            raise SaveValidationError("Invalid crypt slot index") from e

    def to_dict(self) -> Dict[str, Any]:
        return {"items": [i.to_dict() for i in self.items]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Crypt":
        items = [Item.from_dict(it) for it in data.get("items", [])]
        return Crypt(items=items)


@dataclass
class RelicCollection:
    """Tracks which Relics of the Veil the player has collected (persistent)."""

    collected: Set[str] = field(default_factory=set)
    allowed: Set[str] = field(default_factory=lambda: set(DEFAULT_RELIC_IDS))

    def __post_init__(self) -> None:
        # Validate collected relics are within allowed set
        unknown = set(self.collected) - set(self.allowed)
        if unknown:
            raise SaveValidationError(f"Unknown relic ids in collection: {sorted(unknown)}")

    def add(self, relic_id: str) -> None:
        if relic_id not in self.allowed:
            raise SaveValidationError(f"Unknown relic id: {relic_id}")
        self.collected.add(relic_id)

    def has(self, relic_id: str) -> bool:
        return relic_id in self.collected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collected": sorted(list(self.collected)),
            "allowed": sorted(list(self.allowed)),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RelicCollection":
        collected = set(data.get("collected", []))
        allowed = set(data.get("allowed", list(DEFAULT_RELIC_IDS)))
        return RelicCollection(collected=collected, allowed=allowed)


@dataclass
class MetaState:
    """Persistent meta-progression data that survives across runs.

    - ``hub_cycle``: number of Graveyard visits; drives deterministic shop restocks
    - ``meta_seed``: profile-level seed mixed into hub randomness (shop stock)
    - ``runs_completed`` / ``deepest_floor``: lightweight lifetime stats
    """

    relics: RelicCollection = field(default_factory=RelicCollection)
    crypt: Crypt = field(default_factory=Crypt)
    hub_cycle: int = 0
    meta_seed: int = 1337
    runs_completed: int = 0
    deepest_floor: int = 0
    stats: Dict[str, int] = field(default_factory=dict)
    achievements: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        for name in ("hub_cycle", "meta_seed", "runs_completed", "deepest_floor"):
            if not isinstance(getattr(self, name), int):
                raise SaveValidationError(f"MetaState.{name} must be an integer")
        if not isinstance(self.stats, dict) or not all(
            isinstance(k, str) and isinstance(v, int) for k, v in self.stats.items()
        ):
            raise SaveValidationError("MetaState.stats must map strings to integers")
        if not isinstance(self.achievements, set):
            self.achievements = set(self.achievements)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relics": self.relics.to_dict(),
            "crypt": self.crypt.to_dict(),
            "hub_cycle": self.hub_cycle,
            "meta_seed": self.meta_seed,
            "runs_completed": self.runs_completed,
            "deepest_floor": self.deepest_floor,
            "stats": dict(self.stats),
            "achievements": sorted(self.achievements),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MetaState":
        return MetaState(
            relics=RelicCollection.from_dict(data.get("relics", {})),
            crypt=Crypt.from_dict(data.get("crypt", {})),
            hub_cycle=int(data.get("hub_cycle", 0)),
            meta_seed=int(data.get("meta_seed", 1337)),
            runs_completed=int(data.get("runs_completed", 0)),
            deepest_floor=int(data.get("deepest_floor", 0)),
            stats={str(k): int(v) for k, v in (data.get("stats") or {}).items()},
            achievements=set(data.get("achievements") or []),
        )


@dataclass
class RunState:
    """Current run state (not meta). Full save only allowed at Graveyard by policy.

    ``party`` holds serialized players (see ``systems.entities.Player.to_dict``);
    persistence treats them as opaque dicts.
    """

    floor: int = 1
    in_graveyard: bool = True
    rng_seed: int = 0
    party: List[Dict[str, Any]] = field(default_factory=list)
    steps_since_encounter: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not isinstance(self.floor, int) or self.floor < 1 or self.floor > 99:
            raise SaveValidationError("RunState.floor must be an integer between 1 and 99")
        if not isinstance(self.in_graveyard, bool):
            raise SaveValidationError("RunState.in_graveyard must be a boolean")
        if not isinstance(self.rng_seed, int):
            raise SaveValidationError("RunState.rng_seed must be an integer")
        if not isinstance(self.party, list) or not all(isinstance(p, dict) for p in self.party):
            raise SaveValidationError("RunState.party must be a list of dicts")
        if not isinstance(self.steps_since_encounter, int) or self.steps_since_encounter < 0:
            raise SaveValidationError("RunState.steps_since_encounter must be a non-negative int")

    def touch(self) -> None:
        self.last_updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "floor": self.floor,
            "in_graveyard": self.in_graveyard,
            "rng_seed": self.rng_seed,
            "party": [dict(p) for p in self.party],
            "steps_since_encounter": self.steps_since_encounter,
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RunState":
        return RunState(
            floor=int(data.get("floor", 1)),
            in_graveyard=bool(data.get("in_graveyard", True)),
            rng_seed=int(data.get("rng_seed", 0)),
            party=list(data.get("party", []) or []),
            steps_since_encounter=int(data.get("steps_since_encounter", 0)),
            started_at=data.get("started_at") or datetime.now(timezone.utc).isoformat(),
            last_updated_at=data.get("last_updated_at") or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class SaveGame:
    """Top-level save object combining meta state and optional run state."""

    meta: MetaState = field(default_factory=MetaState)
    run: Optional[RunState] = None
    schema_version: int = SCHEMA_VERSION
    profile_id: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            # We allow building the object, but codec should handle migration
            pass
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise SaveValidationError("profile_id must be a non-empty string")

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.meta.to_dict(),
        }
        if self.run is not None:
            data["run"] = self.run.to_dict()
        else:
            data["run"] = None
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SaveGame":
        meta = MetaState.from_dict(data.get("meta", {}))
        run_data = data.get("run")
        run = RunState.from_dict(run_data) if isinstance(run_data, dict) else None
        return SaveGame(
            meta=meta,
            run=run,
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            profile_id=data.get("profile_id", "default"),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
            updated_at=data.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )
