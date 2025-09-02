import json
from pathlib import Path

from amor.tools.tiled_prefab import TiledPrefabLoader


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_extract_prefabs_from_tiled(tmp_path: Path):
    prefabs = {
        "$schema": "prefab",
        "prefabs": [
            {"id": "chest_small", "name": "Small Chest", "properties": {"loot_table": "chest_common", "locked": False}},
            {"id": "portal", "name": "Portal", "properties": {"to": "graveyard"}},
        ]
    }
    prefabs_path = tmp_path / "prefabs.json"
    write_json(prefabs_path, prefabs)

    tiled_map = {
        "type": "map",
        "height": 10,
        "width": 10,
        "tilewidth": 16,
        "tileheight": 16,
        "layers": [
            {
                "type": "objectgroup",
                "name": "Prefabs",
                "objects": [
                    {
                        "id": 1,
                        "name": "",
                        "type": "chest_small",
                        "x": 32,
                        "y": 48,
                        "rotation": 0,
                        "properties": [
                            {"name": "locked", "type": "bool", "value": True},
                            {"name": "quality", "type": "string", "value": "common"}
                        ]
                    },
                    {
                        "id": 2,
                        "name": "",
                        "type": "portal",
                        "x": 64,
                        "y": 16,
                        "rotation": 90,
                        "properties": []
                    }
                ]
            }
        ]
    }
    map_path = tmp_path / "map.json"
    write_json(map_path, tiled_map)

    tool = TiledPrefabLoader()
    defs = tool.load_prefab_defs(prefabs_path)
    mp = tool.load_map(map_path)
    instances = tool.extract_instances(mp, defs)

    assert len(instances) == 2

    chest = next(i for i in instances if i.id == "chest_small")
    assert chest.x == 32
    assert chest.y == 48
    # Overrides default properties
    assert chest.properties["locked"] is True
    # Preserves default where not overridden
    assert chest.properties["loot_table"] == "chest_common"
    assert chest.properties["quality"] == "common"

    portal = next(i for i in instances if i.id == "portal")
    assert portal.rotation == 90
    assert portal.properties["to"] == "graveyard"
