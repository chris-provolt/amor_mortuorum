from __future__ import annotations

import json
from typing import Any, Dict


def canonical_dumps(obj: Dict[str, Any]) -> str:
    """Canonical JSON dump for consistent HMAC signing.

    - No whitespace (compact separators)
    - Keys sorted
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)
