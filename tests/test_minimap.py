import os
import sys

# Ensure we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from amor_mortuorum.minimap import MinimapModel, MinimapRenderer


def test_minimap_model_explore_and_toggle():
    mm = MinimapModel(10, 8)
    # Initially nothing explored
    assert not mm.is_explored(0, 0)

    # Reveal single tile
    assert mm.reveal(3, 4) is True
    assert mm.is_explored(3, 4) is True

    # Reveal same tile again -> not newly added
    assert mm.reveal(3, 4) is False

    # Out-of-bounds should not raise and not add
    assert mm.reveal(-1, 0) is False
    assert mm.reveal(10, 10) is False

    # Renderer toggle should flip enabled state
    renderer = MinimapRenderer(mm)
    assert renderer.enabled is True
    renderer.toggle()
    assert renderer.enabled is False
    renderer.toggle()
    assert renderer.enabled is True


def test_minimap_layout_resize_top_right_anchor():
    mm = MinimapModel(20, 10)
    renderer = MinimapRenderer(mm)

    # Resize to a standard window
    layout = renderer.resize(1000, 800)
    assert layout.tile_size >= 1
    # Ensure it's anchored to top-right within margins (approximate checks)
    assert layout.origin_left <= 1000
    assert layout.origin_bottom <= 800
    assert layout.origin_left + layout.pixel_width <= 1000
    assert layout.origin_bottom + layout.pixel_height <= 800

    # Resize to a very small window; should not crash and sizes positive
    layout2 = renderer.resize(160, 120)
    assert layout2.tile_size >= 1
    assert layout2.pixel_width >= 1
    assert layout2.pixel_height >= 1

    # Very large window; still within window bounds
    layout3 = renderer.resize(4000, 2200)
    assert layout3.origin_left + layout3.pixel_width <= 4000
    assert layout3.origin_bottom + layout3.pixel_height <= 2200


def test_minimap_reveal_many_and_clear():
    mm = MinimapModel(5, 5)
    coords = [(x, x) for x in range(5)] + [(100, 100)]  # include one OOB
    added = mm.reveal_many(coords)
    assert added == 5
    for i in range(5):
        assert mm.is_explored(i, i)
    mm.clear()
    for i in range(5):
        assert not mm.is_explored(i, i)
