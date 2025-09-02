import json
from pathlib import Path

import pytest

from amor.utils.json_loader import (
    DuplicateKeyError,
    JsonFileNotFoundError,
    JsonKeyValidationError,
    JsonParseError,
    JsonSchemaError,
    load_json_directory,
    load_json_file,
)


BASIC_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "value": {"type": "integer", "default": 1},
        "tags": {"type": "array", "items": {"type": "string"}, "default": []},
    },
    "additionalProperties": False,
}


def write_json(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_valid_json_with_schema_and_defaults(tmp_path: Path, caplog):
    # Missing 'value' and 'tags' should be defaulted by schema.
    data = {"id": "item.1", "name": "Potion"}
    file_path = tmp_path / "item.json"
    write_json(file_path, data)

    caplog.clear()
    loaded = load_json_file(file_path, schema=BASIC_SCHEMA)

    assert loaded["id"] == "item.1"
    assert loaded["name"] == "Potion"
    assert loaded["value"] == 1  # default applied
    assert loaded["tags"] == []  # default applied

    # Info log should mention applied defaults
    assert any("Applied default values for missing keys" in rec.message for rec in caplog.records)


def test_missing_required_key_raises_readable_error(tmp_path: Path):
    # Missing id has no default; should raise JsonSchemaError with helpful message
    data = {"name": "Potion"}
    file_path = tmp_path / "bad_item.json"
    write_json(file_path, data)

    with pytest.raises(JsonSchemaError) as ei:
        load_json_file(file_path, schema=BASIC_SCHEMA)

    msg = str(ei.value)
    assert "Schema validation failed" in msg
    assert "Missing required keys" in msg
    assert "id" in msg


def test_explicit_defaults_fill_missing_top_level_keys(tmp_path: Path):
    # Schema requires 'name' but we provide an explicit default for it.
    data = {"id": "item.2"}
    file_path = tmp_path / "item2.json"
    write_json(file_path, data)

    loaded = load_json_file(file_path, schema=BASIC_SCHEMA, defaults={"name": "Unknown"})

    assert loaded["name"] == "Unknown"
    assert loaded["value"] == 1  # schema default still applied


def test_required_keys_parameter_enforced(tmp_path: Path):
    data = {"id": "item.3", "name": "Herb"}
    file_path = tmp_path / "item3.json"
    write_json(file_path, data)

    # Enforce an extra required top-level key beyond schema
    with pytest.raises(JsonKeyValidationError) as ei:
        load_json_file(file_path, schema=BASIC_SCHEMA, required_keys=["id", "name", "rarity"])  # no default provided

    msg = str(ei.value)
    assert "Missing required keys" in msg
    assert "rarity" in msg


def test_invalid_json_raises_parse_error(tmp_path: Path):
    bad = tmp_path / "broken.json"
    bad.write_text("{\n  \"id\": \"x\",\n  \"name\": \"Bad\",\n  \"value\": 1,,\n}", encoding="utf-8")

    with pytest.raises(JsonParseError) as ei:
        load_json_file(bad)

    assert "Failed to parse JSON" in str(ei.value)


def test_directory_loader_returns_indexed_map(tmp_path: Path):
    write_json(tmp_path / "a.json", {"id": "a", "name": "A"})
    write_json(tmp_path / "b.json", {"id": "b", "name": "B", "value": 5})

    indexed = load_json_directory(tmp_path, schema=BASIC_SCHEMA, index_by="id")

    assert set(indexed.keys()) == {"a", "b"}
    assert indexed["a"]["value"] == 1  # default applied
    assert indexed["b"]["value"] == 5


def test_directory_loader_duplicate_index_key(tmp_path: Path):
    write_json(tmp_path / "a1.json", {"id": "dup", "name": "One"})
    write_json(tmp_path / "a2.json", {"id": "dup", "name": "Two"})

    with pytest.raises(DuplicateKeyError):
        load_json_directory(tmp_path, schema=BASIC_SCHEMA, index_by="id", strict_index=True)


def test_file_not_found(tmp_path: Path):
    with pytest.raises(JsonFileNotFoundError):
        load_json_file(tmp_path / "missing.json")


def test_directory_loader_required_index_key_missing(tmp_path: Path):
    write_json(tmp_path / "one.json", {"name": "No ID"})

    with pytest.raises(JsonSchemaError):
        # schema requires id and name -> this should fail during schema validation
        load_json_directory(tmp_path, schema=BASIC_SCHEMA, index_by="id")
