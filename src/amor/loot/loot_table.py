from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List

from amor.core.random import RandomSource
from amor.items.models import Item, ItemQuality

logger = logging.getLogger(__name__)

# Default, in-code item pools by quality
_DEFAULT_ITEM_POOLS: Dict[ItemQuality, List[Item]] = {
    ItemQuality.COMMON: [
        Item(id="potion_minor", name="Minor Health Potion", quality=ItemQuality.COMMON, meta={"heal": 25}),
        Item(id="scroll_identify", name="Scroll of Identify", quality=ItemQuality.COMMON),
        Item(id="torch", name="Torch", quality=ItemQuality.COMMON),
    ],
    ItemQuality.UNCOMMON: [
        Item(id="potion_standard", name="Health Potion", quality=ItemQuality.UNCOMMON, meta={"heal": 50}),
        Item(id="bomb_small", name="Small Bomb", quality=ItemQuality.UNCOMMON, meta={"dmg": 30}),
        Item(id="amulet_copper", name="Copper Amulet", quality=ItemQuality.UNCOMMON, meta={"stat": {"DEF": 1}}),
    ],
    ItemQuality.RARE: [
        Item(id="potion_greater", name="Greater Health Potion", quality=ItemQuality.RARE, meta={"heal": 100}),
        Item(id="scroll_freeze", name="Scroll of Freeze", quality=ItemQuality.RARE, meta={"dmg": 40, "status": "frozen"}),
        Item(id="ring_silver", name="Silver Ring", quality=ItemQuality.RARE, meta={"stat": {"SPD": 2}}),
    ],
    ItemQuality.EPIC: [
        Item(id="elixir", name="Elixir", quality=ItemQuality.EPIC, meta={"heal": 100, "mana": 100}),
        Item(id="bomb_heavy", name="Heavy Bomb", quality=ItemQuality.EPIC, meta={"dmg": 75}),
        Item(id="amulet_sapphire", name="Sapphire Amulet", quality=ItemQuality.EPIC, meta={"stat": {"MAG": 3}}),
    ],
    ItemQuality.LEGENDARY: [
        Item(id="token_resurrection", name="Resurrection Token", quality=ItemQuality.LEGENDARY, meta={"revive": True}),
        Item(id="ring_obsidian", name="Obsidian Ring", quality=ItemQuality.LEGENDARY, meta={"stat": {"ATK": 4, "SPD": 2}}),
    ],
}


def _load_item_pools_from_config() -> Dict[ItemQuality, List[Item]] | None:
    """
    Optionally load item pools from JSON config.
    Schema:
    {"items": [{"id": "...", "name": "...", "quality": "common", "meta": {...}}, ...]}
    """
    try:
        root = Path(__file__).resolve().parents[3]
        cfg_dir = Path(os.environ.get("AMOR_CONFIG_DIR", root / "configs"))
        path = cfg_dir / "loot" / "items.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        items: List[Item] = []
        for raw in data.get("items", []):
            items.append(
                Item(
                    id=str(raw["id"]),
                    name=str(raw.get("name", raw["id"])),
                    quality=ItemQuality(str(raw["quality"]).lower()),
                    meta=dict(raw.get("meta", {})),
                )
            )
        pools: Dict[ItemQuality, List[Item]] = {q: [] for q in ItemQuality}
        for it in items:
            pools[it.quality].append(it)
        logger.info("Loaded %d items from config at %s", len(items), path)
        return pools
    except Exception as e:  # pragma: no cover - defensive path
        logger.exception("Failed to load items config: %s", e)
        return None


def get_item_pools() -> Dict[ItemQuality, List[Item]]:
    pools = _load_item_pools_from_config()
    if pools:
        # Ensure all qualities exist
        for q in ItemQuality:
            pools.setdefault(q, [])
        return pools
    return _DEFAULT_ITEM_POOLS


def choose_item_by_quality(quality: ItemQuality, rng: RandomSource | None = None) -> Item:
    """
    Choose an item from the pool of the given quality.
    Returns a copy of the chosen Item so callers can safely mutate instance-level state.
    """
    if rng is None:
        rng = RandomSource()
    pools = get_item_pools()
    pool = pools.get(quality, [])
    if not pool:
        raise RuntimeError(f"No items available for quality {quality}")
    base = rng.choice(pool)
    return base.copy()


__all__ = ["get_item_pools", "choose_item_by_quality"]
