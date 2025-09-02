from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Dict, List

from .config import Settings
from .rng import RNGManager
from .dungeon.generation import DungeonGenerator, Layout
from .loot.chest import ChestGenerator, ChestContent

logger = logging.getLogger(__name__)


def generate_floor(settings: Settings, floor: int) -> Dict:
    """High-level API to generate a floor layout and chest contents deterministically.

    Returns a serializable dict containing layout and chest data.
    """
    rngm = RNGManager(settings.seed)
    dgen = DungeonGenerator(rngm, width=settings.width, height=settings.height)
    layout: Layout = dgen.generate(floor)

    cgen = ChestGenerator(rngm)
    chest_contents: List[ChestContent] = cgen.generate_for_positions(floor, layout.chests)

    result = {
        "seed_hex": rngm.get_master_seed_hex(),
        "floor": floor,
        "layout": {
            "width": layout.width,
            "height": layout.height,
            "grid": list(layout.grid),
            "chests": list(layout.chests),
            "signature": layout.signature(),
        },
        "chests": [asdict(c) for c in chest_contents],
    }
    return result
