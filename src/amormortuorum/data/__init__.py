"""Static game data: items, enemies, loot tables, tiers, relics, encounters, shop.

Everything here is pure Python and loaded from the JSON files shipped next to
this module. ``GameData.load()`` validates cross-references so a typo in a data
file fails fast at boot instead of deep inside a run.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..errors import AmorError

QUALITIES: Tuple[str, ...] = ("Common", "Uncommon", "Rare", "Epic")
EQUIP_TYPES: Tuple[str, ...] = ("weapon", "armor", "helm", "shield", "accessory")
CONSUMABLE_TYPES: Tuple[str, ...] = ("potion", "scroll", "consumable", "token")
MAX_FLOOR = 99


class DataError(AmorError):
    """Raised when a data file is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    type: str
    quality: str = "Common"
    stackable: bool = True
    max_stack: int = 99
    hp_restore: int = 0
    damage: int = 0
    atk: int = 0
    df: int = 0
    spd: int = 0
    max_hp: int = 0
    revive: bool = False

    @property
    def slot(self) -> Optional[str]:
        """Equipment slot this item occupies, or ``None`` for non-equipment."""
        return self.type if self.type in EQUIP_TYPES else None

    @property
    def is_consumable(self) -> bool:
        return self.type in CONSUMABLE_TYPES and not self.revive

    @property
    def usable_in_combat(self) -> bool:
        return self.is_consumable and (self.hp_restore > 0 or self.damage > 0)


@dataclass(frozen=True)
class EnemyDef:
    id: str
    name: str
    hp: int
    atk: int
    df: int
    spd: int
    mp: int = 0
    behavior: str = "chase"
    xp: int = 0
    gold: int = 0


@dataclass(frozen=True)
class FloorTier:
    name: str
    start: int
    end: int

    def contains(self, floor: int) -> bool:
        return self.start <= floor <= self.end


@dataclass(frozen=True)
class RelicDef:
    id: str
    name: str
    desc: str = ""


@dataclass(frozen=True)
class Formation:
    enemies: Tuple[str, ...]
    weight: int = 1


@dataclass(frozen=True)
class TierEncounters:
    step_chance: float
    formations: Tuple[Formation, ...]


@dataclass(frozen=True)
class ShopEntry:
    price: int
    qty_range: Tuple[int, int]


@dataclass
class GameData:
    items: Dict[str, ItemDef] = field(default_factory=dict)
    enemies: Dict[str, EnemyDef] = field(default_factory=dict)
    loot_tables: Dict[str, Dict[str, int]] = field(default_factory=dict)
    tiers: List[FloorTier] = field(default_factory=list)
    relics: List[RelicDef] = field(default_factory=list)
    encounters: Dict[str, TierEncounters] = field(default_factory=dict)
    shop_pool: Dict[str, ShopEntry] = field(default_factory=dict)

    # Lookups

    def item(self, item_id: str) -> ItemDef:
        try:
            return self.items[item_id]
        except KeyError as e:
            raise DataError(f"Unknown item id: {item_id}") from e

    def has_item(self, item_id: str) -> bool:
        return item_id in self.items

    def enemy(self, enemy_id: str) -> EnemyDef:
        try:
            return self.enemies[enemy_id]
        except KeyError as e:
            raise DataError(f"Unknown enemy id: {enemy_id}") from e

    def tier_for_floor(self, floor: int) -> FloorTier:
        for tier in self.tiers:
            if tier.contains(floor):
                return tier
        raise DataError(f"No tier covers floor {floor}")

    def items_of_quality(self, quality: str) -> List[ItemDef]:
        return [it for it in self.items.values() if it.quality == quality]

    @property
    def relic_ids(self) -> List[str]:
        return [r.id for r in self.relics]

    # Loading

    @classmethod
    def load(cls, root: Union[Path, Any, None] = None) -> "GameData":
        """Load and validate all data files.

        ``root`` may be a filesystem path or any ``importlib.resources`` traversable;
        by default the JSON files packaged with ``amormortuorum.data`` are used.
        """
        if root is None:
            root = resources.files(__name__)
        elif isinstance(root, (str, Path)):
            root = Path(root)

        def read(name: str) -> Any:
            try:
                text = root.joinpath(name).read_text(encoding="utf-8")
            except OSError as e:
                raise DataError(f"Missing data file: {name}") from e
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise DataError(f"Malformed JSON in {name}: {e}") from e

        return cls.from_raw(
            items=read("items.json"),
            enemies=read("enemies.json"),
            loot_tables=read("loot_tables.json"),
            floor_tiers=read("floor_tiers.json"),
            relics=read("relics.json"),
            encounters=read("encounters.json"),
            shop=read("shop.json"),
        )

    @classmethod
    def from_raw(
        cls,
        *,
        items: List[dict],
        enemies: List[dict],
        loot_tables: Dict[str, dict],
        floor_tiers: List[dict],
        relics: List[dict],
        encounters: Dict[str, dict],
        shop: Dict[str, dict],
    ) -> "GameData":
        """Build from already-parsed JSON structures and validate."""
        data = cls()
        data.items = _unique_by_id("items", [_build(ItemDef, raw, "items") for raw in items])
        data.enemies = _unique_by_id(
            "enemies", [_build(EnemyDef, raw, "enemies") for raw in enemies]
        )
        data.tiers = [_build(FloorTier, raw, "floor_tiers") for raw in floor_tiers]
        data.relics = [_build(RelicDef, raw, "relics") for raw in relics]
        data.loot_tables = {
            name: dict(spec.get("quality_weights", {})) for name, spec in loot_tables.items()
        }
        data.encounters = {}
        for name, spec in encounters.items():
            formations = tuple(
                Formation(enemies=tuple(f.get("enemies", ())), weight=int(f.get("weight", 1)))
                for f in spec.get("formations", [])
            )
            data.encounters[name] = TierEncounters(
                step_chance=float(spec.get("step_chance", 0.0)), formations=formations
            )
        data.shop_pool = {}
        for item_id, spec in shop.items():
            low, high = spec.get("qty_range", (1, 1))
            data.shop_pool[item_id] = ShopEntry(
                price=int(spec["price"]), qty_range=(int(low), int(high))
            )
        data.validate()
        return data

    def validate(self) -> None:
        # Items
        for it in self.items.values():
            if it.quality not in QUALITIES:
                raise DataError(f"Item {it.id}: unknown quality {it.quality!r}")
            if it.max_stack < 1:
                raise DataError(f"Item {it.id}: max_stack must be >= 1")
        token = self.items.get("res_token")
        if token is None or not token.revive:
            raise DataError("items.json must define 'res_token' with revive=true")

        # Tiers must cover 1..MAX_FLOOR contiguously
        tiers = sorted(self.tiers, key=lambda t: t.start)
        if not tiers or tiers[0].start != 1 or tiers[-1].end != MAX_FLOOR:
            raise DataError(f"floor_tiers must cover floors 1..{MAX_FLOOR}")
        for prev, nxt in zip(tiers, tiers[1:]):
            if nxt.start != prev.end + 1:
                raise DataError(f"floor_tiers gap/overlap between {prev.name} and {nxt.name}")
        tier_names = {t.name for t in tiers}
        if len(tier_names) != len(tiers):
            raise DataError("floor_tiers names must be unique")

        # Loot tables and encounters keyed by tier name
        for name, weights in self.loot_tables.items():
            if name not in tier_names:
                raise DataError(f"loot_tables: unknown tier {name!r}")
            for q in weights:
                if q not in QUALITIES:
                    raise DataError(f"loot_tables[{name}]: unknown quality {q!r}")
            if sum(weights.values()) <= 0:
                raise DataError(f"loot_tables[{name}]: weights must sum to > 0")
        for name in tier_names:
            if name not in self.loot_tables:
                raise DataError(f"loot_tables: missing tier {name!r}")
            if name not in self.encounters:
                raise DataError(f"encounters: missing tier {name!r}")
        for name, enc in self.encounters.items():
            if name not in tier_names:
                raise DataError(f"encounters: unknown tier {name!r}")
            if not 0.0 <= enc.step_chance <= 1.0:
                raise DataError(f"encounters[{name}]: step_chance must be within 0..1")
            if not enc.formations:
                raise DataError(f"encounters[{name}]: needs at least one formation")
            for f in enc.formations:
                if not f.enemies:
                    raise DataError(f"encounters[{name}]: empty formation")
                for eid in f.enemies:
                    if eid not in self.enemies:
                        raise DataError(f"encounters[{name}]: unknown enemy {eid!r}")

        # Shop
        for item_id, entry in self.shop_pool.items():
            if item_id not in self.items:
                raise DataError(f"shop: unknown item {item_id!r}")
            if entry.qty_range[0] > entry.qty_range[1] or entry.qty_range[0] < 0:
                raise DataError(f"shop[{item_id}]: invalid qty_range")

        # Relics
        relic_ids = [r.id for r in self.relics]
        if len(set(relic_ids)) != len(relic_ids):
            raise DataError("relics ids must be unique")


def _build(cls, raw: dict, source: str):
    try:
        return cls(**raw)
    except TypeError as e:
        raise DataError(f"{source}: bad entry {raw.get('id', raw)!r}: {e}") from e


def _unique_by_id(source: str, entries: list) -> dict:
    out: dict = {}
    for entry in entries:
        if entry.id in out:
            raise DataError(f"{source}: duplicate id {entry.id!r}")
        out[entry.id] = entry
    return out


__all__ = [
    "QUALITIES",
    "EQUIP_TYPES",
    "MAX_FLOOR",
    "DataError",
    "ItemDef",
    "EnemyDef",
    "FloorTier",
    "RelicDef",
    "Formation",
    "TierEncounters",
    "ShopEntry",
    "GameData",
]
