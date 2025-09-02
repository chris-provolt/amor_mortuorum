from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class SaveMeta:
    """Minimal meta-progression snapshot persisted on save in Graveyard.

    This is deliberately lightweight and forward-compatible. Game-state payloads
    (e.g., runtime dungeon state) can be handled elsewhere; here we focus on
    the meta portion per acceptance criteria.
    """

    gold: int
    relics: List[str] = field(default_factory=list)
    crypt_items: List[str] = field(default_factory=list)  # up to 3 managed elsewhere
    player_level: int = 1
    depth: int = 0  # current dungeon floor or 0 at Graveyard
    version: str = "0.1.0"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_json(data: str) -> "SaveMeta":
        payload = json.loads(data)
        return SaveMeta(**payload)
