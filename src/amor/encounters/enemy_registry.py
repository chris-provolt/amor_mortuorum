from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class Enemy:
    """Represents a combatant enemy archetype with a power score for difficulty.

    Fields are intentionally simple and data-agnostic; a real project would load
    these from data files. For this feature we provide a default registry that
    covers tiers 1-10 with sensible stat progression.
    """

    id: str
    name: str
    tier: int  # 1..10
    hp: int
    atk: int
    defense: int
    spd: int

    @property
    def power(self) -> float:
        """A simple heuristic to quantify difficulty contribution of one enemy.

        This blends HP, ATK, DEF, SPD with tuned weights. Higher tiers have
        naturally higher stats, so formations built from higher-tier enemies will
        score higher. This is purely for selection/scaling validation and not
        used for combat resolution.
        """
        # Empirical weights; can be tuned later or replaced with ML/balance curves.
        return self.hp * 0.3 + self.atk * 1.0 + self.defense * 0.5 + self.spd * 0.2 + self.tier * 1.5


class EnemyRegistry:
    """A simple in-memory registry of known enemy archetypes.

    In production, this would likely be populated from data files and support
    variant rolls, elite affixes, etc. For now, it's a deterministic set used to
    validate and score formations.
    """

    def __init__(self, enemies: Optional[Iterable[Enemy]] = None) -> None:
        self._enemies: Dict[str, Enemy] = {}
        if enemies is not None:
            for e in enemies:
                self.add(e)
        else:
            self._bootstrap_defaults()

    def add(self, enemy: Enemy) -> None:
        if enemy.id in self._enemies:
            raise ValueError(f"Duplicate enemy id: {enemy.id}")
        if not (1 <= enemy.tier <= 10):
            raise ValueError(f"Enemy '{enemy.id}' has invalid tier {enemy.tier}; expected 1..10")
        self._enemies[enemy.id] = enemy

    def get(self, enemy_id: str) -> Enemy:
        try:
            return self._enemies[enemy_id]
        except KeyError as e:
            raise KeyError(f"Unknown enemy id: {enemy_id}") from e

    def has(self, enemy_id: str) -> bool:
        return enemy_id in self._enemies

    def _bootstrap_defaults(self) -> None:
        # Tier 1
        self.add(Enemy("slime", "Slime", 1, hp=20, atk=5, defense=2, spd=5))
        self.add(Enemy("rat", "Cave Rat", 1, hp=18, atk=6, defense=2, spd=7))
        self.add(Enemy("bat", "Cave Bat", 1, hp=16, atk=5, defense=1, spd=9))
        # Tier 2
        self.add(Enemy("wolf", "Dire Wolf", 2, hp=32, atk=10, defense=5, spd=10))
        self.add(Enemy("skeleton", "Skeleton", 2, hp=28, atk=9, defense=6, spd=8))
        self.add(Enemy("zombie", "Zombie", 2, hp=34, atk=8, defense=6, spd=5))
        # Tier 3
        self.add(Enemy("imp", "Imp", 3, hp=40, atk=13, defense=7, spd=12))
        self.add(Enemy("spider", "Crypt Spider", 3, hp=42, atk=12, defense=8, spd=11))
        self.add(Enemy("ghoul", "Ghoul", 3, hp=50, atk=14, defense=9, spd=9))
        # Tier 4
        self.add(Enemy("orc", "Orc Raider", 4, hp=60, atk=18, defense=12, spd=10))
        self.add(Enemy("banshee", "Banshee", 4, hp=55, atk=19, defense=10, spd=14))
        self.add(Enemy("wight", "Wight", 4, hp=66, atk=17, defense=13, spd=11))
        # Tier 5
        self.add(Enemy("gargoyle", "Gargoyle", 5, hp=78, atk=20, defense=16, spd=12))
        self.add(Enemy("revenant", "Revenant", 5, hp=85, atk=22, defense=15, spd=13))
        self.add(Enemy("sorcerer", "Dark Sorcerer", 5, hp=70, atk=26, defense=12, spd=15))
        # Tier 6
        self.add(Enemy("dread_knight", "Dread Knight", 6, hp=95, atk=28, defense=20, spd=14))
        self.add(Enemy("vampire_spawn", "Vampire Spawn", 6, hp=88, atk=27, defense=18, spd=18))
        self.add(Enemy("troll", "Cave Troll", 6, hp=110, atk=26, defense=22, spd=9))
        # Tier 7
        self.add(Enemy("lichling", "Lichling", 7, hp=100, atk=32, defense=22, spd=16))
        self.add(Enemy("nightmare", "Nightmare", 7, hp=108, atk=33, defense=21, spd=20))
        self.add(Enemy("basilisk", "Basilisk", 7, hp=120, atk=31, defense=24, spd=14))
        # Tier 8
        self.add(Enemy("death_knight", "Death Knight", 8, hp=130, atk=38, defense=28, spd=17))
        self.add(Enemy("vampire", "Vampire", 8, hp=125, atk=39, defense=26, spd=22))
        self.add(Enemy("chimera", "Chimera", 8, hp=140, atk=37, defense=30, spd=16))
        # Tier 9
        self.add(Enemy("archlich", "Archlich", 9, hp=145, atk=42, defense=31, spd=21))
        self.add(Enemy("dread_wraith", "Dread Wraith", 9, hp=138, atk=41, defense=30, spd=25))
        self.add(Enemy("hydra", "Hydra", 9, hp=160, atk=40, defense=34, spd=14))
        # Tier 10
        self.add(Enemy("abyssal_lord", "Abyssal Lord", 10, hp=190, atk=50, defense=38, spd=22))
        self.add(Enemy("dracolich", "Dracolich", 10, hp=200, atk=48, defense=40, spd=20))
        self.add(Enemy("leviathan", "Leviathan", 10, hp=210, atk=47, defense=42, spd=18))
