from __future__ import annotations

import json
from typing import Any, Dict

from .models import SaveGame, SCHEMA_VERSION
from .errors import SaveValidationError


def encode_save(save: SaveGame) -> str:
    """Encode a SaveGame to a pretty-printed JSON string."""
    data = save.to_dict()
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)


def decode_save(text: str) -> SaveGame:
    """Decode JSON text into a SaveGame with version validation and migration hooks."""
    try:
        data: Dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as e:
        raise SaveValidationError(f"Invalid JSON: {e}") from e

    version = int(data.get("schema_version", SCHEMA_VERSION))
    if version != SCHEMA_VERSION:
        data = migrate_data(data, from_version=version, to_version=SCHEMA_VERSION)

    return SaveGame.from_dict(data)


def migrate_data(data: Dict[str, Any], from_version: int, to_version: int) -> Dict[str, Any]:
    """Migrate data between schema versions. Implement stepwise migrations as needed.

    Currently SCHEMA_VERSION=1, so no migrations are performed.
    """
    if from_version == to_version:
        return data

    if from_version > to_version:
        # Save file from the future. We can try to accept, but warn via exception.
        raise SaveValidationError(
            f"Save schema version {from_version} is newer than supported {to_version}."
        )

    # Example scaffold for future migrations:
    # for v in range(from_version, to_version):
    #     if v == 1:
    #         data = migrate_v1_to_v2(data)
    #     elif v == 2:
    #         data = migrate_v2_to_v3(data)
    # etc.

    # Since no migrations are defined, just set version
    data["schema_version"] = to_version
    return data
