"""Runtime entities: player stats, equipment, inventory, enemies.

Pure Python; serializable with ``to_dict``/``from_dict`` so a run can be stored
in ``persistence.RunState``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..data import EQUIP_TYPES, EnemyDef, GameData, ItemDef
from ..errors import InsufficientGold, InvalidOperation

logger = logging.getLogger(__name__)

EQUIP_SLOTS: Tuple[str, ...] = EQUIP_TYPES

# Level-1 baseline for a new wanderer.
BASE_STATS = {"max_hp": 40, "max_mp": 8, "atk": 7, "df": 3, "spd": 5}
STARTING_GOLD = 50


@dataclass
class Stats:
    max_hp: int = 30
    hp: int = 30
    max_mp: int = 5
    mp: int = 5
    atk: int = 6
    df: int = 2
    spd: int = 5

    def to_dict(self) -> Dict[str, int]:
        return {
            "max_hp": self.max_hp,
            "hp": self.hp,
            "max_mp": self.max_mp,
            "mp": self.mp,
            "atk": self.atk,
            "df": self.df,
            "spd": self.spd,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Stats":
        base = Stats()
        return Stats(
            max_hp=int(data.get("max_hp", base.max_hp)),
            hp=int(data.get("hp", data.get("max_hp", base.hp))),
            max_mp=int(data.get("max_mp", base.max_mp)),
            mp=int(data.get("mp", data.get("max_mp", base.mp))),
            atk=int(data.get("atk", base.atk)),
            df=int(data.get("df", base.df)),
            spd=int(data.get("spd", base.spd)),
        )


@dataclass
class Inventory:
    """Stacks of items keyed by item id."""

    items: Dict[str, int] = field(default_factory=dict)

    def count(self, item_id: str) -> int:
        return self.items.get(item_id, 0)

    def has(self, item_id: str, quantity: int = 1) -> bool:
        return self.count(item_id) >= quantity

    def add(self, item: ItemDef, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Quantity to add must be positive")
        new_total = self.count(item.id) + quantity
        limit = item.max_stack if item.stackable else 1
        if new_total > limit:
            raise InvalidOperation(
                f"Exceeds max stack for {item.name}: {new_total} > {limit}"
            )
        self.items[item.id] = new_total

    def remove(self, item: ItemDef, quantity: int = 1) -> None:
        if quantity <= 0:
            raise InvalidOperation("Quantity to remove must be positive")
        current = self.count(item.id)
        if current < quantity:
            raise InvalidOperation(
                f"Cannot remove {quantity}x {item.name}; only {current} in inventory"
            )
        remaining = current - quantity
        if remaining == 0:
            self.items.pop(item.id, None)
        else:
            self.items[item.id] = remaining

    def ids(self) -> List[str]:
        return list(self.items)

    def to_dict(self) -> Dict[str, int]:
        return dict(self.items)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Inventory":
        return Inventory(items={str(k): int(v) for k, v in (data or {}).items() if int(v) > 0})


@dataclass
class Equipment:
    """One item id (or None) per equip slot."""

    slots: Dict[str, Optional[str]] = field(
        default_factory=lambda: {slot: None for slot in EQUIP_SLOTS}
    )

    def equip(self, item: ItemDef) -> Optional[str]:
        """Equip ``item`` into its slot; return the replaced item id, if any."""
        slot = item.slot
        if slot is None:
            raise InvalidOperation(f"{item.name} is not equipment")
        previous = self.slots.get(slot)
        self.slots[slot] = item.id
        return previous

    def unequip(self, slot: str) -> Optional[str]:
        if slot not in self.slots:
            raise InvalidOperation(f"Unknown equip slot: {slot}")
        previous = self.slots[slot]
        self.slots[slot] = None
        return previous

    def bonus(self, data: GameData) -> Tuple[int, int, int, int]:
        """Total (atk, df, spd, max_hp) from equipped items."""
        atk = df = spd = max_hp = 0
        for item_id in self.slots.values():
            if item_id is None or not data.has_item(item_id):
                continue
            it = data.item(item_id)
            atk += it.atk
            df += it.df
            spd += it.spd
            max_hp += it.max_hp
        return atk, df, spd, max_hp

    def to_dict(self) -> Dict[str, Optional[str]]:
        return dict(self.slots)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Equipment":
        eq = Equipment()
        for slot, item_id in (data or {}).items():
            if slot in eq.slots:
                eq.slots[slot] = str(item_id) if item_id else None
        return eq


@dataclass
class Player:
    name: str = "Wanderer"
    level: int = 1
    xp: int = 0
    gold: int = STARTING_GOLD
    stats: Stats = field(default_factory=Stats)
    equipment: Equipment = field(default_factory=Equipment)
    inventory: Inventory = field(default_factory=Inventory)
    # Which companion template this member came from (None for the leader).
    companion_id: Optional[str] = None
    # Derived modifiers (relic passives); recomputed from meta, never persisted.
    bonuses: Dict[str, int] = field(default_factory=dict)

    # Derived stats

    def bonus(self, key: str) -> int:
        return self.bonuses.get(key, 0)

    def effective_atk(self, data: GameData) -> int:
        return self.stats.atk + self.equipment.bonus(data)[0] + self.bonus("atk")

    def effective_df(self, data: GameData) -> int:
        return self.stats.df + self.equipment.bonus(data)[1] + self.bonus("df")

    def effective_spd(self, data: GameData) -> int:
        return self.stats.spd + self.equipment.bonus(data)[2] + self.bonus("spd")

    def effective_max_hp(self, data: GameData) -> int:
        return self.stats.max_hp + self.equipment.bonus(data)[3]

    # Health

    @property
    def is_alive(self) -> bool:
        return self.stats.hp > 0

    @property
    def hp(self) -> int:
        return self.stats.hp

    @property
    def max_hp(self) -> int:
        return self.stats.max_hp

    def heal(self, amount: int) -> int:
        """Heal up to ``amount``; return HP actually restored."""
        if amount <= 0:
            return 0
        before = self.stats.hp
        self.stats.hp = min(self.stats.max_hp, self.stats.hp + amount)
        return self.stats.hp - before

    def restore_mp(self, amount: int) -> int:
        """Restore up to ``amount`` MP; return MP actually restored."""
        if amount <= 0:
            return 0
        before = self.stats.mp
        self.stats.mp = min(self.stats.max_mp, self.stats.mp + amount)
        return self.stats.mp - before

    def spend_mp(self, amount: int) -> None:
        if amount > self.stats.mp:
            raise InvalidOperation(f"{self.name} lacks the MP ({self.stats.mp}/{amount})")
        self.stats.mp -= amount

    def known_skills(self, data: GameData):
        return data.skills_known_at(self.level)

    def heal_full(self) -> None:
        logger.debug("Healing %s to full: %s -> %s", self.name, self.stats.hp, self.stats.max_hp)
        self.stats.hp = self.stats.max_hp
        self.stats.mp = self.stats.max_mp

    def take_damage(self, amount: int) -> int:
        dealt = max(0, min(self.stats.hp, amount))
        self.stats.hp -= dealt
        return dealt

    # Gold

    def spend_gold(self, amount: int) -> None:
        if amount < 0:
            raise InvalidOperation("Cannot spend negative gold")
        if self.gold < amount:
            raise InsufficientGold(f"Insufficient gold: have {self.gold}, need {amount}")
        self.gold -= amount

    def add_gold(self, amount: int) -> None:
        if amount < 0:
            raise InvalidOperation("Cannot add negative gold")
        self.gold += amount

    # Items

    def has_item(self, item_id: str) -> bool:
        return self.inventory.has(item_id)

    def equip_from(self, bag: Inventory, item: ItemDef, data: GameData) -> Optional[str]:
        """Move ``item`` from ``bag`` into its slot; the previous item returns to ``bag``."""
        if not bag.has(item.id):
            raise InvalidOperation(f"{item.name} is not in the bag")
        bag.remove(item, 1)
        previous = self.equipment.equip(item)
        if previous is not None and data.has_item(previous):
            bag.add(data.item(previous), 1)
        return previous

    def unequip_to(self, bag: Inventory, slot: str, data: GameData) -> Optional[str]:
        """Move the item in ``slot`` into ``bag``. Returns its id, or None if empty."""
        item_id = self.equipment.slots.get(slot)
        if item_id is None:
            return None
        bag.add(data.item(item_id), 1)  # may raise on a full stack
        self.equipment.unequip(slot)
        return item_id

    def use_consumable_from(self, bag: Inventory, item: ItemDef) -> int:
        """Use a restorative consumable from ``bag`` outside combat. Returns HP restored."""
        if not bag.has(item.id):
            raise InvalidOperation(f"{item.name} is not in the bag")
        if not item.is_consumable or (item.hp_restore <= 0 and item.mp_restore <= 0):
            raise InvalidOperation(f"{item.name} cannot be used here")
        bag.remove(item, 1)
        self.restore_mp(item.mp_restore)
        return self.heal(item.hp_restore)

    # Own-inventory conveniences (the leader's bag is the party bag)

    def equip_from_inventory(self, item: ItemDef, data: GameData) -> Optional[str]:
        return self.equip_from(self.inventory, item, data)

    def unequip_to_inventory(self, slot: str, data: GameData) -> Optional[str]:
        return self.unequip_to(self.inventory, slot, data)

    def use_consumable(self, item: ItemDef) -> int:
        return self.use_consumable_from(self.inventory, item)

    # Serialization

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "stats": self.stats.to_dict(),
            "equipment": self.equipment.to_dict(),
            "inventory": self.inventory.to_dict(),
            "companion_id": self.companion_id,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Player":
        return Player(
            name=str(data.get("name", "Wanderer")),
            level=int(data.get("level", 1)),
            xp=int(data.get("xp", 0)),
            gold=int(data.get("gold", 0)),
            stats=Stats.from_dict(data.get("stats", {})),
            equipment=Equipment.from_dict(data.get("equipment", {})),
            inventory=Inventory.from_dict(data.get("inventory", {})),
            companion_id=data.get("companion_id") or None,
        )


def new_player(name: str = "Wanderer") -> Player:
    stats = Stats(
        max_hp=BASE_STATS["max_hp"],
        hp=BASE_STATS["max_hp"],
        max_mp=BASE_STATS["max_mp"],
        mp=BASE_STATS["max_mp"],
        atk=BASE_STATS["atk"],
        df=BASE_STATS["df"],
        spd=BASE_STATS["spd"],
    )
    return Player(name=name, stats=stats, gold=STARTING_GOLD)


@dataclass
class Enemy:
    def_id: str
    name: str
    stats: Stats
    xp: int = 0
    gold: int = 0
    boss: bool = False
    enrage: int = 0

    @staticmethod
    def from_def(d: EnemyDef) -> "Enemy":
        return Enemy(
            def_id=d.id,
            name=d.name,
            stats=Stats(max_hp=d.hp, hp=d.hp, max_mp=d.mp, mp=d.mp, atk=d.atk, df=d.df, spd=d.spd),
            xp=d.xp,
            gold=d.gold,
            boss=d.boss,
            enrage=d.enrage,
        )

    @property
    def is_enraged(self) -> bool:
        """Below half HP a boss enters its second phase and hits harder."""
        return self.enrage > 0 and self.stats.hp * 2 <= self.stats.max_hp

    @property
    def is_alive(self) -> bool:
        return self.stats.hp > 0

    def take_damage(self, amount: int) -> int:
        dealt = max(0, min(self.stats.hp, amount))
        self.stats.hp -= dealt
        return dealt
