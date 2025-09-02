import builtins
import types

import pytest

from amor_mortuorum.rendering.chunked_batch import (
    ChunkedSpriteBatch,
    DummySpriteFactory,
    ViewRect,
)


def make_batch(tile=32, chunk=128, layers=("floor", "walls")):
    return ChunkedSpriteBatch(tile_size=tile, chunk_pixel_size=chunk, layers=layers, sprite_factory=DummySpriteFactory())


def populate_grid(batch: ChunkedSpriteBatch, grid_w: int, grid_h: int, chunk_px: int):
    # Place one tile at center of each chunk in a grid of size grid_w x grid_h starting at (0,0)
    for cy in range(grid_h):
        for cx in range(grid_w):
            x = cx * chunk_px + chunk_px / 2
            y = cy * chunk_px + chunk_px / 2
            batch.add_tile(x, y, texture=None, layer="floor")
            batch.add_tile(x + 8, y + 8, texture=None, layer="walls")


def test_visible_chunk_selection():
    chunk_px = 128
    batch = make_batch(chunk=chunk_px)
    # Create 3x3 chunks with content (0..2, 0..2)
    populate_grid(batch, 3, 3, chunk_px)

    # Viewport entirely within chunk (1,1)
    vp = ViewRect(left=chunk_px + 10, bottom=chunk_px + 10, width=50, height=50)
    batch.draw(vp)
    assert batch.num_chunks_visible_last == 1

    # Viewport straddles four center chunks: (1,1), (2,1), (1,2), (2,2)
    vp2 = ViewRect(left=chunk_px + (chunk_px // 2), bottom=chunk_px + (chunk_px // 2), width=chunk_px, height=chunk_px)
    batch.draw(vp2)
    assert batch.num_chunks_visible_last == 4


def test_draw_calls_only_for_visible_chunks_and_non_empty_layers():
    chunk_px = 128
    batch = make_batch(chunk=chunk_px)
    populate_grid(batch, 2, 1, chunk_px)  # chunks (0,0) and (1,0)

    # Narrow viewport only covering first chunk
    vp = ViewRect(left=0, bottom=0, width=chunk_px - 1, height=chunk_px - 1)
    batch.draw(vp)

    # Estimate visible tiles should be sum of both layers in first chunk: 2
    assert batch.estimate_visible_tiles_last() == 2


def test_add_and_remove_tiles_updates_state():
    batch = make_batch()
    t1 = batch.add_tile(10, 10, texture=None, layer="floor")
    t2 = batch.add_tile(42, 42, texture=None, layer="walls")

    assert batch.num_tiles_total == 2
    assert batch.num_chunks_total >= 1

    assert batch.remove_tile(t1) is True
    assert batch.num_tiles_total == 1

    assert batch.remove_tile(9999) is False


def test_layer_order_respected_in_draw():
    # Custom factory to record draw order
    class RecordingList:
        def __init__(self, name: str):
            self.name = name
            self._sprites = []
            self.drawn = 0

        def append(self, sprite):
            self._sprites.append(sprite)

        def remove(self, sprite):
            self._sprites.remove(sprite)

        def draw(self):
            self.drawn += 1
            order.append(self.name)

        def __len__(self):
            return len(self._sprites)

    class RecFactory(DummySpriteFactory):
        def __init__(self, chunk_to_layer):
            self.chunk_to_layer = chunk_to_layer

        def create_sprite_list(self):
            # Name is filled after insertion based on chunk/layer context in test
            # We patch after creation in the batch's internal mapping.
            return RecordingList("unknown")

    order = []
    chunk_px = 128
    layers = ["floor", "walls", "objects"]
    # Create batch with our recording factory
    batch = ChunkedSpriteBatch(tile_size=32, chunk_pixel_size=chunk_px, layers=layers, sprite_factory=RecFactory({}))

    # Add one tile per layer in two chunks (0,0) and (1,0)
    # We'll swap in names for lists after they're created to track draw order
    ids = []
    ids.append(batch.add_tile(10, 10, texture=None, layer="floor"))     # chunk (0,0)
    ids.append(batch.add_tile(10, 10, texture=None, layer="walls"))     # chunk (0,0)
    ids.append(batch.add_tile(10, 10, texture=None, layer="objects"))   # chunk (0,0)
    ids.append(batch.add_tile(130, 10, texture=None, layer="floor"))    # chunk (1,0)
    ids.append(batch.add_tile(130, 10, texture=None, layer="walls"))    # chunk (1,0)

    # Patch names for each existing spritelist to be "layer@chunk"
    # Access batch internals for testing draw order intent
    for (cx, cy), layer_map in batch._chunks.items():  # noqa: SLF001 - test utility
        for lname, sl in layer_map.items():
            if isinstance(sl, RecordingList):
                sl.name = f"{lname}@{cx},{cy}"

    vp = ViewRect(left=0, bottom=0, width=300, height=100)
    batch.draw(vp)

    # Expect layer-major ordering: floor over both chunks, then walls over both, then objects
    # Only chunks with content for that layer appear
    expected = [
        "floor@0,0",
        "floor@1,0",
        "walls@0,0",
        "walls@1,0",
        "objects@0,0",
    ]
    assert order == expected


def test_visible_chunk_keys_only_existing_chunks():
    chunk_px = 128
    batch = make_batch(chunk=chunk_px)
    # Add a single tile in chunk (5,5)
    batch.add_tile(5 * chunk_px + 10, 5 * chunk_px + 10, texture=None, layer="floor")

    # Viewport covers a large area including many potential chunks
    vp = ViewRect(left=0, bottom=0, width=6 * chunk_px, height=6 * chunk_px)
    batch.draw(vp)
    # Only existing chunk(s) should be considered visible
    assert batch.num_chunks_visible_last == 1
