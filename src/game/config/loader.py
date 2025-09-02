from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

try:  # Python 3.9+
    from importlib.resources import files as resource_files
except ImportError:  # pragma: no cover - fallback
    from importlib_resources import files as resource_files  # type: ignore

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MinibossConfig:
    floors: List[int]
    lock_reason: str = "miniboss_gate"


def load_miniboss_config(path: Optional[str] = None) -> MinibossConfig:
    """Load miniboss gate configuration from YAML.

    If path is None, loads the embedded default resource at
    game/config/miniboss.yaml.
    """
    if path is None:
        data = resource_files("game.config").joinpath("miniboss.yaml").read_text(encoding="utf-8")
        logger.debug("Loaded embedded miniboss config resource")
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        logger.debug("Loaded miniboss config from path: %s", path)

    raw = yaml.safe_load(data) or {}
    floors = list(sorted(set(int(x) for x in raw.get("floors", [20, 40, 60, 80]))))
    lock_reason = str(raw.get("lock_reason", "miniboss_gate"))
    logger.info("Miniboss floors: %s | lock_reason=%s", floors, lock_reason)
    return MinibossConfig(floors=floors, lock_reason=lock_reason)
