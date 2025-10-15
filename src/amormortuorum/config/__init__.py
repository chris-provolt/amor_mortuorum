from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


# Default item catalog, can be overridden by data files later.
DEFAULT_ITEMS: Dict[str, Dict] = {
    "potion_small": {
        "id": "potion_small",
        "name": "Minor Healing Potion",
        "type": "potion",
        "stackable": True,
        "max_stack": 99,
        "meta": False,
    },
    "scroll_embers": {
        "id": "scroll_embers",
        "name": "Scroll of Embers",
        "type": "scroll",
        "stackable": True,
        "max_stack": 20,
        "meta": False,
    },
    "antidote": {
        "id": "antidote",
        "name": "Antidote",
        "type": "consumable",
        "stackable": True,
        "max_stack": 50,
        "meta": False,
    },
}


# Shop pool configuration: defines price and per-cycle quantity range per item.
# The shop will include all items in the pool each cycle, but with a limited
# stock chosen uniformly at random within the range.
DEFAULT_SHOP_POOL: Dict[str, Dict] = {
    "potion_small": {"price": 20, "qty_range": (2, 5)},
    "scroll_embers": {"price": 45, "qty_range": (1, 3)},
    "antidote": {"price": 18, "qty_range": (1, 4)},
}


@dataclass(frozen=True)
class Paths:
    base: Path
    save_dir: Path
    save_file: Path


def get_paths(root: Path | None = None) -> Paths:
    """Compute default paths for save storage.

    Args:
        root: Optional root directory. If not provided, use user data dir.

    Returns:
        Paths: structured locations for saves.
    """
    if root is None:
        # Default user-specific path
        base = Path.home() / ".amor_mortuorum"
    else:
        base = Path(root)
    save_dir = base / "saves"
    save_file = save_dir / "meta.json"
    return Paths(base=base, save_dir=save_dir, save_file=save_file)


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
