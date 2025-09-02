import os
import sys

# Add src to path for test execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

# We avoid importing arcade in tests to keep them headless; test the logic side only.
from amor_mortuorum.game import DungeonMap
from amor_mortuorum.minimap import MinimapModel, MinimapRenderer


def test_dungeon_map_generation_and_minimap_update():
    world = DungeonMap(32, 24)
    # World should have rooms
    assert len(world.rooms) >= 1

    # Spawn at first room center
    rx, ry, rw, rh = world.rooms[0]
    px, py = rx + rw // 2, ry + rh // 2

    mm = MinimapModel(world.width, world.height)
    renderer = MinimapRenderer(mm)

    # Initial resize should not crash
    layout = renderer.resize(800, 600)
    assert layout.tile_size >= 1

    # Reveal around the player
    revealed = 0
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if world.is_room(px + dx, py + dy):
                revealed += 1 if mm.reveal(px + dx, py + dy) else 0
    assert revealed >= 1

    # Simulate movement to a walkable neighbor and reveal
    moved = False
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        if world.is_walkable(px + dx, py + dy):
            px += dx
            py += dy
            moved = True
            break
    assert moved is True

    # Reveal at new position
    newly = mm.reveal(px, py)
    assert newly in (True, False)  # call works and doesn't crash

    # Another resize after some exploration; should not crash
    layout2 = renderer.resize(1024, 768)
    assert layout2.tile_size >= 1
