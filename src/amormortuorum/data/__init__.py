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
FORMATION_BEHAVIOURS: Tuple[str, ...] = ("hunter", "guard", "skittish")


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
    mp_restore: int = 0
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
        return self.is_consumable and (
            self.hp_restore > 0 or self.mp_restore > 0 or self.damage > 0
        )


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
    boss: bool = False
    enrage: int = 0  # extra ATK once below half HP (a simple second phase)


@dataclass(frozen=True)
class FloorTier:
    name: str
    start: int
    end: int

    def contains(self, floor: int) -> bool:
        return self.start <= floor <= self.end


PASSIVE_KEYS: Tuple[str, ...] = ("atk", "df", "spd", "fov", "gold_pct", "xp_pct")
SKILL_TARGETS: Tuple[str, ...] = ("enemy", "all_enemies", "ally")


@dataclass(frozen=True)
class SkillDef:
    id: str
    name: str
    mp: int
    target: str = "enemy"
    damage: int = 0
    heal: int = 0
    learn_level: int = 1
    desc: str = ""

    @property
    def is_offensive(self) -> bool:
        return self.damage > 0


@dataclass(frozen=True)
class RelicDef:
    id: str
    name: str
    desc: str = ""
    passive: Dict[str, int] = field(default_factory=dict)

    @property
    def is_final(self) -> bool:
        return self.id == "veil_final"


@dataclass(frozen=True)
class Formation:
    enemies: Tuple[str, ...]
    weight: int = 1
    behaviour: Optional[str] = None  # map behaviour; None = from the lead enemy


@dataclass(frozen=True)
class TierEncounters:
    step_chance: float
    formations: Tuple[Formation, ...]


@dataclass(frozen=True)
class ShopEntry:
    price: int
    qty_range: Tuple[int, int]


@dataclass(frozen=True)
class BossDef:
    floor: int
    name: str
    enemies: Tuple[str, ...]
    relic_id: Optional[str] = None
    final: bool = False


STAT_KEYS: Tuple[str, ...] = ("max_hp", "max_mp", "atk", "df", "spd")


@dataclass(frozen=True)
class CompanionDef:
    id: str
    name: str
    cost: int
    stats: Dict[str, int] = field(default_factory=dict)
    desc: str = ""


TRACKED_STATS: Tuple[str, ...] = (
    "runs_started", "runs_won", "deaths", "revives", "deepest_floor", "battles_won",
    "enemies_slain", "bosses_slain", "chests_opened", "gold_earned", "steps", "relics",
    "bounties", "ambushes",
)


@dataclass(frozen=True)
class AchievementDef:
    id: str
    name: str
    stat: str
    at_least: int
    desc: str = ""


@dataclass(frozen=True)
class Balance:
    """Global tuning knobs (data/balance.json)."""

    enemy_atk_per_floor: float = 0.45
    enemy_df_per_floor: float = 0.2
    enemy_hp_per_floor: float = 0.025
    enemy_spd_per_floor: float = 0.05
    enemy_xp_per_floor: float = 0.03
    enemy_gold_per_floor: float = 0.03
    encounter_cap: float = 0.2
    encounter_growth_per_step: float = 0.05
    monsters_base: float = 3.0           # roaming groups on B1
    monsters_per_floor: float = 0.04     # extra groups per floor of depth
    monster_respawn_chance: float = 0.01  # per step, while below strength

    @staticmethod
    def from_raw(raw: dict) -> "Balance":
        known = {f for f in Balance.__dataclass_fields__}
        return Balance(**{k: float(v) for k, v in raw.items() if k in known})


@dataclass(frozen=True)
class XpCurve:
    """``thresholds[i]`` is the total XP needed to reach level ``i + 1``."""

    max_level: int = 30
    thresholds: Tuple[int, ...] = tuple(int(20 * (n ** 1.6)) for n in range(30))
    per_level: Dict[str, int] = field(
        default_factory=lambda: {"max_hp": 6, "max_mp": 1, "atk": 1}
    )
    # stat -> period: +1 on every level divisible by the period
    every: Dict[str, int] = field(default_factory=lambda: {"df": 2, "spd": 3})

    @property
    def spd_every(self) -> int:
        return self.every.get("spd", 1)

    def xp_for_level(self, level: int) -> int:
        level = max(1, min(level, self.max_level))
        return self.thresholds[level - 1]

    def level_for_xp(self, xp: int) -> int:
        level = 1
        for i, needed in enumerate(self.thresholds):
            if xp >= needed:
                level = i + 1
            else:
                break
        return min(level, self.max_level)

    @staticmethod
    def from_raw(raw: dict) -> "XpCurve":
        every = {k: int(v) for k, v in raw.get("every", {}).items()}
        if "spd_every" in raw and "spd" not in every:  # legacy key
            every["spd"] = int(raw["spd_every"])
        return XpCurve(
            max_level=int(raw.get("max_level", 30)),
            thresholds=tuple(int(t) for t in raw.get("thresholds", ())),
            per_level={k: int(v) for k, v in raw.get("per_level", {}).items()},
            every=every or {"df": 2, "spd": 3},
        )


@dataclass
class GameData:
    items: Dict[str, ItemDef] = field(default_factory=dict)
    enemies: Dict[str, EnemyDef] = field(default_factory=dict)
    loot_tables: Dict[str, Dict[str, int]] = field(default_factory=dict)
    tiers: List[FloorTier] = field(default_factory=list)
    relics: List[RelicDef] = field(default_factory=list)
    encounters: Dict[str, TierEncounters] = field(default_factory=dict)
    shop_pool: Dict[str, ShopEntry] = field(default_factory=dict)
    xp_curve: XpCurve = field(default_factory=XpCurve)
    bosses: Dict[int, BossDef] = field(default_factory=dict)
    skills: Dict[str, SkillDef] = field(default_factory=dict)
    companions: Dict[str, CompanionDef] = field(default_factory=dict)
    balance: Balance = field(default_factory=Balance)
    achievements: List[AchievementDef] = field(default_factory=list)

    # Lookups

    def companion(self, companion_id: str) -> CompanionDef:
        try:
            return self.companions[companion_id]
        except KeyError as e:
            raise DataError(f"Unknown companion id: {companion_id}") from e

    def skill(self, skill_id: str) -> SkillDef:
        try:
            return self.skills[skill_id]
        except KeyError as e:
            raise DataError(f"Unknown skill id: {skill_id}") from e

    def skills_known_at(self, level: int) -> List[SkillDef]:
        """Skills a character of ``level`` knows, in learning order."""
        known = [sk for sk in self.skills.values() if sk.learn_level <= level]
        return sorted(known, key=lambda sk: (sk.learn_level, sk.id))

    def boss_for_floor(self, floor: int) -> Optional[BossDef]:
        return self.bosses.get(floor)

    @property
    def boss_floors(self) -> List[int]:
        return sorted(self.bosses)

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

    def relic(self, relic_id: str) -> RelicDef:
        for r in self.relics:
            if r.id == relic_id:
                return r
        raise DataError(f"Unknown relic id: {relic_id}")

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
            xp_curve=read("xp_curve.json"),
            bosses=read("bosses.json"),
            skills=read("skills.json"),
            companions=read("companions.json"),
            balance=read("balance.json"),
            achievements=read("achievements.json"),
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
        xp_curve: Optional[dict] = None,
        bosses: Optional[Dict[str, dict]] = None,
        skills: Optional[List[dict]] = None,
        companions: Optional[List[dict]] = None,
        balance: Optional[dict] = None,
        achievements: Optional[List[dict]] = None,
    ) -> "GameData":
        """Build from already-parsed JSON structures and validate."""
        data = cls()
        data.achievements = [
            _build(AchievementDef, raw, "achievements") for raw in (achievements or [])
        ]
        if balance:
            data.balance = Balance.from_raw(balance)
        data.companions = _unique_by_id(
            "companions", [_build(CompanionDef, raw, "companions") for raw in (companions or [])]
        )
        data.skills = _unique_by_id(
            "skills", [_build(SkillDef, raw, "skills") for raw in (skills or [])]
        )
        if xp_curve is not None:
            data.xp_curve = XpCurve.from_raw(xp_curve)
        for floor_key, spec in (bosses or {}).items():
            floor = int(floor_key)
            data.bosses[floor] = BossDef(
                floor=floor,
                name=str(spec.get("name", f"Boss of B{floor}")),
                enemies=tuple(spec.get("enemies", ())),
                relic_id=spec.get("relic_id"),
                final=bool(spec.get("final", False)),
            )
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
                Formation(
                    enemies=tuple(f.get("enemies", ())),
                    weight=int(f.get("weight", 1)),
                    behaviour=f.get("behaviour"),
                )
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
                if f.behaviour is not None and f.behaviour not in FORMATION_BEHAVIOURS:
                    raise DataError(
                        f"encounters[{name}]: unknown behaviour {f.behaviour!r}"
                    )

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
        for relic in self.relics:
            for key, value in relic.passive.items():
                if key not in PASSIVE_KEYS:
                    raise DataError(f"relics[{relic.id}]: unknown passive {key!r}")
                if not isinstance(value, int):
                    raise DataError(f"relics[{relic.id}]: passive {key!r} must be an int")

        # Bosses
        relic_ids_set = {r.id for r in self.relics}
        for floor, boss in self.bosses.items():
            if not 1 <= floor <= MAX_FLOOR:
                raise DataError(f"bosses: floor {floor} out of range")
            if not boss.enemies:
                raise DataError(f"bosses[{floor}]: needs at least one enemy")
            for eid in boss.enemies:
                if eid not in self.enemies:
                    raise DataError(f"bosses[{floor}]: unknown enemy {eid!r}")
            if boss.relic_id is not None and boss.relic_id not in relic_ids_set:
                raise DataError(f"bosses[{floor}]: unknown relic {boss.relic_id!r}")
        finals = [b for b in self.bosses.values() if b.final]
        if len(finals) > 1:
            raise DataError("bosses: only one final boss allowed")
        if finals and finals[0].floor != MAX_FLOOR:
            raise DataError(f"bosses: the final boss must be on floor {MAX_FLOOR}")

        # Skills
        for sk in self.skills.values():
            if sk.target not in SKILL_TARGETS:
                raise DataError(f"skills[{sk.id}]: unknown target {sk.target!r}")
            if sk.mp < 0 or sk.learn_level < 1:
                raise DataError(f"skills[{sk.id}]: mp must be >= 0 and learn_level >= 1")
            if (sk.damage > 0) == (sk.heal > 0):
                raise DataError(f"skills[{sk.id}]: needs exactly one of damage or heal")
            if sk.heal > 0 and sk.target != "ally":
                raise DataError(f"skills[{sk.id}]: healing skills target an ally")
            if sk.damage > 0 and sk.target == "ally":
                raise DataError(f"skills[{sk.id}]: damaging skills target enemies")

        # Companions
        for comp in self.companions.values():
            if comp.cost < 0:
                raise DataError(f"companions[{comp.id}]: cost must be >= 0")
            for key in STAT_KEYS:
                if key not in comp.stats or not isinstance(comp.stats[key], int):
                    raise DataError(f"companions[{comp.id}]: stats need integer {key!r}")
            if comp.stats["max_hp"] < 1:
                raise DataError(f"companions[{comp.id}]: max_hp must be >= 1")

        # Achievements
        seen_ach = set()
        for ach in self.achievements:
            if ach.id in seen_ach:
                raise DataError(f"achievements: duplicate id {ach.id!r}")
            seen_ach.add(ach.id)
            if ach.stat not in TRACKED_STATS:
                raise DataError(f"achievements[{ach.id}]: unknown stat {ach.stat!r}")
            if ach.at_least < 1:
                raise DataError(f"achievements[{ach.id}]: at_least must be >= 1")

        # Balance
        b = self.balance
        for name in ("enemy_atk_per_floor", "enemy_df_per_floor", "enemy_hp_per_floor",
                     "enemy_spd_per_floor", "enemy_xp_per_floor", "enemy_gold_per_floor",
                     "encounter_growth_per_step", "monsters_base", "monsters_per_floor"):
            if getattr(b, name) < 0:
                raise DataError(f"balance: {name} must be >= 0")
        if not 0.0 < b.encounter_cap <= 1.0:
            raise DataError("balance: encounter_cap must be within (0, 1]")
        if not 0.0 <= b.monster_respawn_chance <= 1.0:
            raise DataError("balance: monster_respawn_chance must be within 0..1")

        # XP curve
        curve = self.xp_curve
        if curve.max_level < 1 or len(curve.thresholds) != curve.max_level:
            raise DataError("xp_curve: thresholds must have exactly max_level entries")
        if curve.thresholds[0] != 0:
            raise DataError("xp_curve: level 1 must start at 0 XP")
        if any(b <= a for a, b in zip(curve.thresholds, curve.thresholds[1:])):
            raise DataError("xp_curve: thresholds must be strictly increasing")
        for stat, period in curve.every.items():
            if period < 1:
                raise DataError(f"xp_curve: every[{stat!r}] must be >= 1")


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
    "PASSIVE_KEYS",
    "MAX_FLOOR",
    "FORMATION_BEHAVIOURS",
    "DataError",
    "ItemDef",
    "EnemyDef",
    "FloorTier",
    "RelicDef",
    "Formation",
    "TierEncounters",
    "ShopEntry",
    "XpCurve",
    "BossDef",
    "SkillDef",
    "SKILL_TARGETS",
    "CompanionDef",
    "Balance",
    "AchievementDef",
    "TRACKED_STATS",
    "GameData",
]
