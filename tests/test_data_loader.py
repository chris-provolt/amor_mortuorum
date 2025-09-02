import json
from pathlib import Path
import pytest

from amor.data.loader import DataLoader, DataValidationError, SchemaRegistry


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_loader_validates_item(tmp_path: Path):
    # Create a valid item
    item = {
        "$schema": "item",
        "id": "potion_minor",
        "name": "Minor Potion",
        "type": "consumable",
        "rarity": "common",
        "stackSize": 3,
        "effects": [{"id": "heal", "amount": 25}],
    }
    p = tmp_path / "item.json"
    write_json(p, item)

    loader = DataLoader()
    data = loader.load(p)
    assert data["id"] == "potion_minor"


def test_loader_rejects_invalid_item(tmp_path: Path):
    # Missing required field 'id'
    item = {
        "$schema": "item",
        "name": "Nameless",
        "type": "consumable",
        "rarity": "common",
    }
    p = tmp_path / "bad_item.json"
    write_json(p, item)

    loader = DataLoader()
    with pytest.raises(DataValidationError) as ei:
        loader.load(p)
    assert "validation failed" in str(ei.value).lower()
    human = ei.value.to_human()
    assert "id" in human


def test_include_object_merge(tmp_path: Path):
    base = {"a": 1, "nested": {"x": 1, "y": 2}}
    write_json(tmp_path / "base.json", base)
    doc = {"$include": "base.json", "nested": {"y": 42}, "b": 2}
    p = tmp_path / "doc.json"
    write_json(p, doc)

    loader = DataLoader()
    data = loader.load(p, validate=False)
    assert data["a"] == 1
    assert data["b"] == 2
    assert data["nested"] == {"x": 1, "y": 42}


def test_include_array_expansion(tmp_path: Path):
    arr = [1, 2, 3]
    write_json(tmp_path / "arr.json", arr)
    doc = {"list": [{"$include": "arr.json"}, 4]}
    p = tmp_path / "doc.json"
    write_json(p, doc)

    loader = DataLoader()
    data = loader.load(p, validate=False)
    assert data["list"] == [1, 2, 3, 4]


def test_cycle_detection(tmp_path: Path):
    write_json(tmp_path / "a.json", {"$include": "b.json"})
    write_json(tmp_path / "b.json", {"$include": "a.json"})

    loader = DataLoader()
    with pytest.raises(ValueError):
        loader.load(tmp_path / "a.json", validate=False)
