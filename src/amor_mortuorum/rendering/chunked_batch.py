from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union, Protocol

logger = logging.getLogger(__name__)


# --------- Viewport/Rect utilities ---------
@dataclass(frozen=True)
class ViewRect:
    """Axis-aligned rectangle describing the current camera viewport in world pixels.

    Attributes:
        left: Left X coordinate (inclusive)
        bottom: Bottom Y coordinate (inclusive)
        width: Width in pixels
        height: Height in pixels
    """

    left: float
    bottom: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def top(self) -> float:
        return self.bottom + self.height

    def intersects(self, other: "ViewRect") -> bool:
        return not (
            self.right <= other.left
            or other.right <= self.left
            or self.top <= other.bottom
            or other.top <= self.bottom
        )

    @classmethod
    def from_tuple(
        cls, rect: Union[Tuple[float, float, float, float], List[float]]
    ) -> "ViewRect":
        left, bottom, width, height = rect
        return cls(left, bottom, width, height)


# --------- Sprite List Abstractions ---------
class SpriteLike(Protocol):
    """A minimal protocol to represent an engine-specific sprite.

    Implementations should be compatible with arcade.Sprite enough to be
    added/removed to SpriteLists and drawn. In tests, a dummy implementation
    is provided to avoid requiring an OpenGL context.
    """

    center_x: float
    center_y: float


class SpriteListLike(Protocol):
    """A minimal protocol for a batch that can draw multiple sprites at once."""

    def append(self, sprite: SpriteLike) -> None:
        ...

    def remove(self, sprite: SpriteLike) -> None:
        ...

    def draw(self) -> None:
        ...

    def __len__(self) -> int:
        ...


class SpriteFactory(Protocol):
    """Factory for creating sprites and sprite lists.

    Use ArcadeSpriteFactory in production. Tests use a dummy to avoid GL.
    """

    def create_sprite(self, texture: Optional[str], center_x: float, center_y: float, scale: float = 1.0, angle: float = 0.0) -> SpriteLike:
        ...

    def create_sprite_list(self) -> SpriteListLike:
        ...


class _DummySprite:
    def __init__(self, center_x: float, center_y: float) -> None:
        self.center_x = center_x
        self.center_y = center_y
        # Optional: additional properties to simulate engine sprite


class _DummySpriteList:
    def __init__(self) -> None:
        self._sprites: List[_DummySprite] = []
        self.draw_count: int = 0  # for testing/metrics

    def append(self, sprite: _DummySprite) -> None:
        self._sprites.append(sprite)

    def remove(self, sprite: _DummySprite) -> None:
        try:
            self._sprites.remove(sprite)
        except ValueError:
            pass

    def draw(self) -> None:
        # No-op draw (headless). Increment counter for tests.
        self.draw_count += 1

    def __len__(self) -> int:
        return len(self._sprites)


class DummySpriteFactory(SpriteFactory):
    """Headless factory used in tests or CLI tools without a GL context."""

    def create_sprite(self, texture: Optional[str], center_x: float, center_y: float, scale: float = 1.0, angle: float = 0.0) -> _DummySprite:
        return _DummySprite(center_x=center_x, center_y=center_y)

    def create_sprite_list(self) -> _DummySpriteList:
        return _DummySpriteList()


class ArcadeSpriteFactory(SpriteFactory):
    """Factory that uses arcade.Sprite and arcade.SpriteList under the hood.

    Import is deferred to runtime to keep tests headless.
    """

    def __init__(self) -> None:
        try:
            import arcade  # type: ignore
        except Exception as e:  # pragma: no cover - runtime only
            raise RuntimeError(
                "ArcadeSpriteFactory requires the 'arcade' package at runtime"
            ) from e
        self._arcade = arcade

    def create_sprite(self, texture: Optional[str], center_x: float, center_y: float, scale: float = 1.0, angle: float = 0.0):  # pragma: no cover - requires arcade
        arcade = self._arcade
        # texture can be None if pre-baked into a texture atlas/tileset; callers may set later
        sprite = arcade.Sprite(texture if texture else None, scale=scale, angle=angle)
        sprite.center_x = center_x
        sprite.center_y = center_y
        return sprite

    def create_sprite_list(self):  # pragma: no cover - requires arcade
        arcade = self._arcade
        # Use SpriteList with spatial hashing disabled (draw culling is chunk-based)
        return arcade.SpriteList()


# --------- Chunked sprite batching ---------
@dataclass
class _TileRecord:
    tile_id: int
    chunk_key: Tuple[int, int]
    layer: str
    sprite: SpriteLike


class ChunkedSpriteBatch:
    """Chunked sprite batching with draw culling based on camera viewport.

    This renderer addresses two performance pillars:
    - Sprite batching: Uses engine-level SpriteList to batch draw calls.
    - Draw culling: Splits the world into fixed-size chunks (in pixels) and
      only draws SpriteLists for chunks that intersect the visible viewport.

    Design highlights:
    - Stable performance independent of total tiles; O(visible_chunks) draw calls.
    - No per-frame churn: tiles are added/removed when the map changes, not
      during camera movement.
    - Layered: deterministic draw ordering of layers across visible chunks.

    Typical usage:
        batch = ChunkedSpriteBatch(tile_size=32, chunk_pixel_size=1024, layers=["floor", "walls", "objects"])
        batch.add_tile(x * 32, y * 32, texture_path, layer="floor")
        ...
        # Each frame:
        batch.draw(ViewRect(left, bottom, width, height))
    """

    def __init__(
        self,
        tile_size: int,
        chunk_pixel_size: int = 1024,
        layers: Union[int, Iterable[str]] = ("base",),
        sprite_factory: Optional[SpriteFactory] = None,
    ) -> None:
        if isinstance(layers, int):
            self._layers: List[str] = [str(i) for i in range(layers)]
        else:
            self._layers = list(layers)
            if not self._layers:
                raise ValueError("layers must be a non-empty iterable of layer names")

        if chunk_pixel_size <= 0:
            raise ValueError("chunk_pixel_size must be > 0")
        if tile_size <= 0:
            raise ValueError("tile_size must be > 0")

        self.tile_size = tile_size
        self.chunk_pixel_size = chunk_pixel_size
        self._sprite_factory: SpriteFactory = sprite_factory or DummySpriteFactory()

        # Map of (cx, cy) -> layer -> SpriteListLike
        self._chunks: Dict[Tuple[int, int], Dict[str, SpriteListLike]] = {}
        # tile_id -> _TileRecord
        self._tiles: Dict[int, _TileRecord] = {}
        # For stats/visibility tracking
        self._last_visible_chunks: List[Tuple[int, int]] = []

        self._next_tile_id: int = 1

        logger.debug(
            "ChunkedSpriteBatch initialized: tile_size=%s, chunk_pixel_size=%s, layers=%s",
            tile_size,
            chunk_pixel_size,
            self._layers,
        )

    # ---- Public API ----
    @property
    def layers(self) -> List[str]:
        return self._layers

    def add_tile(
        self,
        x: float,
        y: float,
        texture: Optional[str],
        layer: Optional[Union[str, int]] = None,
        *,
        scale: float = 1.0,
        angle: float = 0.0,
    ) -> int:
        """Add a tile sprite at world position (x, y) and return its tile_id.

        Args:
            x, y: world coordinates (pixels), typically the tile center.
            texture: path/identifier for the sprite's texture (engine-dependent).
            layer: layer name or index; defaults to the first configured layer.
            scale: sprite scale.
            angle: sprite rotation angle.
        """
        if layer is None:
            layer_name = self._layers[0]
        else:
            layer_name = str(layer)
            if layer_name not in self._layers:
                raise ValueError(f"Unknown layer '{layer_name}'. Known: {self._layers}")

        sprite = self._sprite_factory.create_sprite(texture, x, y, scale=scale, angle=angle)
        key = self._chunk_key_for_point(x, y)
        spritelist = self._get_or_create_chunk_layer(key, layer_name)
        spritelist.append(sprite)

        tile_id = self._next_tile_id
        self._next_tile_id += 1

        self._tiles[tile_id] = _TileRecord(tile_id, key, layer_name, sprite)
        logger.debug("Added tile id=%s @(%s,%s) layer=%s chunk=%s", tile_id, x, y, layer_name, key)
        return tile_id

    def remove_tile(self, tile_id: int) -> bool:
        """Remove a previously added tile by id. Returns True if removed."""
        rec = self._tiles.pop(tile_id, None)
        if rec is None:
            logger.debug("remove_tile called for unknown id=%s", tile_id)
            return False
        layer_map = self._chunks.get(rec.chunk_key)
        if layer_map is None:
            return False
        spritelist = layer_map.get(rec.layer)
        if spritelist is None:
            return False
        spritelist.remove(rec.sprite)
        logger.debug("Removed tile id=%s from chunk=%s layer=%s", tile_id, rec.chunk_key, rec.layer)
        return True

    def clear(self) -> None:
        """Remove all tiles and chunks."""
        self._chunks.clear()
        self._tiles.clear()
        self._last_visible_chunks.clear()
        self._next_tile_id = 1
        logger.debug("Cleared all tiles and chunks")

    def draw(self, viewport: Union[ViewRect, Tuple[float, float, float, float], List[float]], *, layers: Optional[Iterable[Union[str, int]]] = None) -> None:
        """Draw visible chunks intersecting the viewport.

        Args:
            viewport: ViewRect or (left, bottom, width, height)
            layers: Optional subset of layers to draw (names or indices). Draw order
                    respects the configured layer ordering.
        """
        if not isinstance(viewport, ViewRect):
            viewport = ViewRect.from_tuple(viewport)  # type: ignore

        visible_keys = self._visible_chunk_keys(viewport)
        self._last_visible_chunks = visible_keys

        draw_layers: List[str]
        if layers is None:
            draw_layers = self._layers
        else:
            draw_layers = []
            allowed = {str(l) for l in layers}
            for lname in self._layers:
                if lname in allowed:
                    draw_layers.append(lname)

        # Draw in layer order, then over visible chunks. This maintains deterministic
        # layering across the world while preventing per-sprite calls.
        for layer_name in draw_layers:
            for key in visible_keys:
                layer_map = self._chunks.get(key)
                if not layer_map:
                    continue
                spritelist = layer_map.get(layer_name)
                if spritelist and len(spritelist) > 0:
                    spritelist.draw()

    # ---- Stats & Debugging ----
    @property
    def num_tiles_total(self) -> int:
        return len(self._tiles)

    @property
    def num_chunks_total(self) -> int:
        return len(self._chunks)

    @property
    def num_chunks_visible_last(self) -> int:
        return len(self._last_visible_chunks)

    def estimate_visible_tiles_last(self) -> int:
        total = 0
        for key in self._last_visible_chunks:
            layer_map = self._chunks.get(key)
            if not layer_map:
                continue
            for sl in layer_map.values():
                total += len(sl)
        return total

    # ---- Internals ----
    def _get_or_create_chunk_layer(self, key: Tuple[int, int], layer_name: str) -> SpriteListLike:
        layer_map = self._chunks.get(key)
        if layer_map is None:
            layer_map = {}
            self._chunks[key] = layer_map
        spritelist = layer_map.get(layer_name)
        if spritelist is None:
            spritelist = self._sprite_factory.create_sprite_list()
            layer_map[layer_name] = spritelist
        return spritelist

    def _chunk_key_for_point(self, x: float, y: float) -> Tuple[int, int]:
        cx = int(x // self.chunk_pixel_size)
        cy = int(y // self.chunk_pixel_size)
        return (cx, cy)

    def _chunk_rect(self, key: Tuple[int, int]) -> ViewRect:
        cx, cy = key
        return ViewRect(
            left=cx * self.chunk_pixel_size,
            bottom=cy * self.chunk_pixel_size,
            width=self.chunk_pixel_size,
            height=self.chunk_pixel_size,
        )

    def _visible_chunk_keys(self, viewport: ViewRect) -> List[Tuple[int, int]]:
        # Compute inclusive range of chunk indices intersecting viewport
        first_cx = int(viewport.left // self.chunk_pixel_size)
        last_cx = int((viewport.right - 1) // self.chunk_pixel_size)
        first_cy = int(viewport.bottom // self.chunk_pixel_size)
        last_cy = int((viewport.top - 1) // self.chunk_pixel_size)

        keys: List[Tuple[int, int]] = []
        for cy in range(first_cy, last_cy + 1):
            for cx in range(first_cx, last_cx + 1):
                key = (cx, cy)
                # Only consider chunks that exist to keep draw iteration minimal
                if key in self._chunks:
                    keys.append(key)
        return keys


__all__ = [
    "ChunkedSpriteBatch",
    "ViewRect",
    "SpriteFactory",
    "ArcadeSpriteFactory",
    "DummySpriteFactory",
]
