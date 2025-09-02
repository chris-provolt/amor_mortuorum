import os
from pathlib import Path

import pytest

from amor.procgen.tiled_prefab import TiledPrefab, GridMap, PrefabStamper, StampOptions


def write_tmx(tmp_path: Path) -> Path:
    # Minimal TMX map: 4x3 tiles, CSV data, 1 tile layer and 1 collisions object layer
    content = """<?xml version="1.0" encoding="UTF-8"?>
<map version="1.8" tiledversion="1.8.6" orientation="orthogonal" renderorder="right-down" width="4" height="3" tilewidth="16" tileheight="16" infinite="0" nextlayerid="3" nextobjectid="2">
 <tileset firstgid="1" name="dummy" tilewidth="16" tileheight="16" tilecount="1" columns="1">
  <image source="dummy.png" width="16" height="16"/>
 </tileset>
 <layer id="1" name="Tiles" width="4" height="3">
  <data encoding="csv">
1,1,0,0,
1,1,0,0,
0,0,0,0
  </data>
 </layer>
 <objectgroup id="2" name="Collisions">
  <!-- Rectangle covering tiles (1,0) and (1,1) given tile size 16x16 -->
  <object id="1" x="16" y="0" width="16" height="32"/>
 </objectgroup>
</map>
"""
    tmx_path = tmp_path / "prefab.tmx"
    tmx_path.write_text(content, encoding="utf-8")
    return tmx_path


def test_load_tmx_and_basic_properties(tmp_path: Path):
    tmx_path = write_tmx(tmp_path)
    prefab = TiledPrefab.from_tmx(str(tmx_path))
    assert prefab.width == 4
    assert prefab.height == 3
    assert prefab.tilewidth == 16
    assert prefab.tileheight == 16
    # Primary layer should be named 'Tiles'
    assert prefab.primary_layer.name == "Tiles"
    # Check tile values
    # Top-left 2x2 should be 1s
    for y in range(2):
        for x in range(2):
            assert prefab.primary_layer.gid_at(x, y) == 1
    # Collisions at (1,0) and (1,1)
    assert prefab.solid_at(1, 0) is True
    assert prefab.solid_at(1, 1) is True
    assert prefab.solid_at(0, 0) is False


def test_stamp_success_and_collisions_applied(tmp_path: Path):
    tmx_path = write_tmx(tmp_path)
    prefab = TiledPrefab.from_tmx(str(tmx_path))

    # Create a 10x10 grid map
    g = GridMap(10, 10)
    # Stamp at (2,3)
    ok = PrefabStamper.stamp(g, prefab, 2, 3)
    assert ok is True

    # Tiles should be stamped at (2,3),(3,3),(2,4),(3,4)
    for x, y in [(2, 3), (3, 3), (2, 4), (3, 4)]:
        assert g.get_tile(x, y) == 1

    # Collisions from prefab should be applied at offset (1,0) and (1,1) -> (3,3) and (3,4)
    assert g.is_blocked(3, 3) is True
    assert g.is_blocked(3, 4) is True
    # Neighbor not in collisions mask remains unblocked
    assert g.is_blocked(2, 3) is False


def test_stamp_respects_existing_collisions(tmp_path: Path):
    tmx_path = write_tmx(tmp_path)
    prefab = TiledPrefab.from_tmx(str(tmx_path))

    g = GridMap(10, 10)
    # Pre-block a cell that prefab would touch: prefab collision at local (1,0) => global (5,6)
    g.set_blocked(5, 6, True)

    # Attempt to stamp at (4,6) should fail due to collision overlap
    ok = PrefabStamper.stamp(g, prefab, 4, 6, options=StampOptions(respect_collisions=True))
    assert ok is False

    # Ensure no tiles were written at the expected positions
    assert g.get_tile(4, 6) == 0
    assert g.get_tile(5, 6) == 0


def test_stamp_out_of_bounds_fails(tmp_path: Path):
    tmx_path = write_tmx(tmp_path)
    prefab = TiledPrefab.from_tmx(str(tmx_path))

    g = GridMap(5, 5)
    # Placing at (3,3) would exceed (3+4 > 5)
    ok = PrefabStamper.stamp(g, prefab, 3, 3)
    assert ok is False


def test_can_override_collision_respect(tmp_path: Path):
    tmx_path = write_tmx(tmp_path)
    prefab = TiledPrefab.from_tmx(str(tmx_path))

    g = GridMap(10, 10)
    # Pre-block a cell that prefab would touch
    g.set_blocked(3, 3, True)

    # With respect_collisions=False, placement is allowed (though usually not recommended)
    ok = PrefabStamper.stamp(g, prefab, 2, 3, options=StampOptions(respect_collisions=False))
    assert ok is True

    # Tiles still stamped
    assert g.get_tile(2, 3) == 1
    assert g.get_tile(3, 3) == 1


def test_invalid_encoding_rejected(tmp_path: Path):
    # Same as write_tmx but with base64 encoding -> should raise ValueError
    content = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<map version=\"1.8\" tiledversion=\"1.8.6\" orientation=\"orthogonal\" renderorder=\"right-down\" width=\"2\" height=\"2\" tilewidth=\"16\" tileheight=\"16\" infinite=\"0\" nextlayerid=\"2\" nextobjectid=\"1\"> 
 <layer id=\"1\" name=\"Tiles\" width=\"2\" height=\"2\"> 
  <data encoding=\"base64\">AAAA</data> 
 </layer> 
</map> 
"""
    tmx_path = tmp_path / "bad.tmx"
    tmx_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        TiledPrefab.from_tmx(str(tmx_path))
