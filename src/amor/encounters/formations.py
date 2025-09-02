from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .enemy_registry import EnemyRegistry, Enemy

logger = logging.getLogger(__name__)

# Public constants
MIN_TIER = 1
MAX_TIER = 10


def floor_to_tier(floor: int) -> int:
    """Maps a dungeon floor (1..99) to a difficulty tier (1..10).

    Floors 1-10 => tier 1, 11-20 => tier 2, ..., 91-99 => tier 10.
    We clamp outside values for robustness.
    """
    if floor is None:
        return MIN_TIER
    if floor < 1:
        return MIN_TIER
    # Use 10-floor buckets, last tier covers 91-99
    tier = ((floor - 1) // 10) + 1
    if tier < MIN_TIER:
        return MIN_TIER
    if tier > MAX_TIER:
        return MAX_TIER
    return tier


@dataclass(frozen=True)
class FormationMember:
    enemy: str
    count: int


@dataclass(frozen=True)
class Formation:
    id: str
    members: Tuple[FormationMember, ...]
    weights: Dict[str, int]  # string keys "1".."10" for JSON simplicity

    def weight_for_tier(self, tier: int) -> int:
        return int(self.weights.get(str(tier), 0))


@dataclass
class FormationSet:
    """Collection of formations with validation against the enemy registry.

    Provides helper utilities for weighted selection and difficulty estimation.
    """

    formations: Tuple[Formation, ...]
    registry: EnemyRegistry

    def formations_for_tier(self, tier: int) -> List[Formation]:
        return [f for f in self.formations if f.weight_for_tier(tier) > 0]

    def select_for_tier(self, tier: int, rng: Optional[random.Random] = None) -> Formation:
        rng = rng or random
        candidates = self.formations_for_tier(tier)
        if not candidates:
            raise ValueError(f"No formations available for tier {tier}")
        weights = [f.weight_for_tier(tier) for f in candidates]
        total = sum(weights)
        if total <= 0:
            raise ValueError(f"All formation weights are zero for tier {tier}")
        pick = rng.uniform(0, total)
        acc = 0.0
        for f, w in zip(candidates, weights):
            acc += w
            if pick <= acc:
                logger.debug("Selected formation %s for tier %s (roll=%.3f/%d)", f.id, tier, pick, total)
                return f
        # Fallback due to floating point rounding
        logger.debug("Fallback selection: returning last candidate for tier %s", tier)
        return candidates[-1]

    def spawn(self, formation: Formation) -> List[Tuple[Enemy, int]]:
        """Resolve a formation into concrete enemy archetypes + counts."""
        resolved = []
        for m in formation.members:
            e = self.registry.get(m.enemy)
            resolved.append((e, m.count))
        return resolved

    def formation_difficulty(self, formation: Formation) -> float:
        return sum(self.registry.get(m.enemy).power * m.count for m in formation.members)

    def expected_difficulty_for_tier(self, tier: int) -> float:
        candidates = self.formations_for_tier(tier)
        weights = [f.weight_for_tier(tier) for f in candidates]
        total = float(sum(weights))
        if total <= 0:
            raise ValueError(f"Cannot compute difficulty: no weighted formations for tier {tier}")
        weighted = 0.0
        for f, w in zip(candidates, weights):
            weighted += self.formation_difficulty(f) * (w / total)
        return weighted


class FormationSelector:
    """High-level API for consumers to get a spawn list for a given floor.

    Provides deterministic selection with an optional RNG instance.
    """

    def __init__(self, formation_set: FormationSet) -> None:
        self._set = formation_set

    def select_for_floor(self, floor: int, rng: Optional[random.Random] = None) -> List[Tuple[Enemy, int]]:
        tier = floor_to_tier(floor)
        f = self._set.select_for_tier(tier, rng=rng)
        return self._set.spawn(f)


# Loading and validation

def _parse_member(obj: dict) -> FormationMember:
    if not isinstance(obj, dict):
        raise ValueError(f"Formation member must be an object, got {type(obj)}")
    enemy = obj.get("enemy")
    count = obj.get("count")
    if not isinstance(enemy, str) or not enemy:
        raise ValueError("Formation member 'enemy' must be a non-empty string")
    if not isinstance(count, int) or count <= 0:
        raise ValueError("Formation member 'count' must be a positive integer")
    return FormationMember(enemy=enemy, count=count)


def _parse_formation(obj: dict) -> Formation:
    if not isinstance(obj, dict):
        raise ValueError("Formation must be an object")
    fid = obj.get("id")
    if not isinstance(fid, str) or not fid:
        raise ValueError("Formation 'id' must be a non-empty string")
    members = obj.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError(f"Formation '{fid}' must have a non-empty list of members")
    weights = obj.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError(f"Formation '{fid}' must have a non-empty weights object")
    # Validate weight keys/values
    norm_weights: Dict[str, int] = {}
    for k, v in weights.items():
        if not isinstance(k, str) or not k.isdigit():
            raise ValueError(f"Formation '{fid}' has invalid weight tier key: {k}")
        if int(k) < MIN_TIER or int(k) > MAX_TIER:
            raise ValueError(f"Formation '{fid}' has out-of-range tier key {k}")
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"Formation '{fid}' has non-negative integer weight for tier {k}")
        norm_weights[k] = v

    parsed_members = tuple(_parse_member(m) for m in members)
    return Formation(id=fid, members=parsed_members, weights=norm_weights)


def load_formations_from_dict(data: dict, registry: Optional[EnemyRegistry] = None) -> FormationSet:
    """Load formations from an in-memory dict adhering to the schema used in JSON.

    Schema:
    {
      "formations": [
        {
          "id": "...",
          "members": [{"enemy": "slime", "count": 2}, ...],
          "weights": {"1": 10, "2": 5, ...}
        },
        ...
      ]
    }
    """
    if not isinstance(data, dict):
        raise ValueError("Formations data must be an object")
    raw_list = data.get("formations")
    if not isinstance(raw_list, list) or not raw_list:
        raise ValueError("'formations' must be a non-empty list")

    formations = tuple(_parse_formation(o) for o in raw_list)
    reg = registry or EnemyRegistry()

    # Validate that all enemy ids exist and that formation members are sensible
    for f in formations:
        for m in f.members:
            if not reg.has(m.enemy):
                raise ValueError(f"Formation '{f.id}' references unknown enemy id '{m.enemy}'")
            if m.count <= 0:
                raise ValueError(f"Formation '{f.id}' member '{m.enemy}' has invalid count {m.count}")
        # Ensure at least one positive weight exists
        if sum(f.weights.values()) <= 0:
            raise ValueError(f"Formation '{f.id}' has no positive weights across tiers")

    fs = FormationSet(formations=formations, registry=reg)

    # Optional sanity checks: ensure monotonic access to higher-tier enemies
    # (not mandatory, but helpful for data hygiene). We'll log warnings if a formation
    # includes enemies from higher tiers than any tier weight non-zero.
    for f in formations:
        max_enemy_tier = max(reg.get(m.enemy).tier for m in f.members)
        allowed_tiers = [int(k) for k, w in f.weights.items() if w > 0]
        if allowed_tiers and min(allowed_tiers) < max_enemy_tier - 1:
            # This heuristic allows a formation to introduce an enemy up to 1 tier higher than the floor tier,
            # but warns if it's earlier than that. Adjust as balance needs.
            logger.warning(
                "Formation '%s' may appear too early: enemy tier up to %d but has weight in tier %d",
                f.id,
                max_enemy_tier,
                min(allowed_tiers),
            )

    return fs


def load_formations_from_path(path: Path | str, registry: Optional[EnemyRegistry] = None) -> FormationSet:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Formations file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    return load_formations_from_dict(data, registry=registry)
