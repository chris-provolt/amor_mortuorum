import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple, Iterable
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class TileLayer:
    """Represents a single tile layer in a Tiled TMX map.

    Attributes:
        name: Layer name.
        width: Number of tiles horizontally.
        height: Number of tiles vertically.
        data: 2D grid [y][x] of GIDs (0 means empty/no tile).
    """
    name: str
    width: int
    height: int
    data: List[List[int]]

    def gid_at(self, x: int, y: int) -> int:
        return self.data[y][x]

    def __repr__(self) -> str:  # pragma: no cover - for debugging only
        return f"TileLayer(name={self.name!r}, {self.width}x{self.height})"


class MapAdapter:
    """Abstract adapter for interacting with a dungeon grid/map.

    Implementations must provide methods for querying and modifying tile IDs and
    collision flags on a grid with dimensions width x height.
    """

    def get_size(self) -> Tuple[int, int]:
        raise NotImplementedError

    def get_tile(self, x: int, y: int) -> int:
        raise NotImplementedError

    def set_tile(self, x: int, y: int, gid: int) -> None:
        raise NotImplementedError

    def is_blocked(self, x: int, y: int) -> bool:
        raise NotImplementedError

    def set_blocked(self, x: int, y: int, blocked: bool) -> None:
        raise NotImplementedError


class GridMap(MapAdapter):
    """Simple in-memory grid implementation for testing and integration.

    Stores an integer tile layer and a boolean collision mask.
    """

    def __init__(self, width: int, height: int, default_gid: int = 0, default_blocked: bool = False) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("GridMap width and height must be positive")
        self.width = width
        self.height = height
        self._tiles: List[List[int]] = [[default_gid for _ in range(width)] for _ in range(height)]
        self._blocked: List[List[bool]] = [[default_blocked for _ in range(width)] for _ in range(height)]

    def get_size(self) -> Tuple[int, int]:
        return self.width, self.height

    def get_tile(self, x: int, y: int) -> int:
        return self._tiles[y][x]

    def set_tile(self, x: int, y: int, gid: int) -> None:
        self._tiles[y][x] = gid

    def is_blocked(self, x: int, y: int) -> bool:
        return self._blocked[y][x]

    def set_blocked(self, x: int, y: int, blocked: bool) -> None:
        self._blocked[y][x] = blocked

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"GridMap({self.width}x{self.height})"


class TiledPrefab:
    """Prefab loaded from a Tiled (.tmx) file.

    Supports basic orthogonal maps with CSV-encoded tile layers and an optional
    Object Layer named "Collisions" (or similar) containing rectangle objects
    denoting blocked tiles. Collisions will be rasterized per tile.

    Limitations:
    - Only encoding="csv" tile data is supported (no base64/compression).
    - Orthogonal maps only.
    - Collision objects: rectangles are supported. Other shapes are ignored.
    - Tile GIDs are preserved as-is; any tileset images are ignored.
    """

    def __init__(
        self,
        width: int,
        height: int,
        tilewidth: int,
        tileheight: int,
        tile_layers: List[TileLayer],
        collision_mask: Optional[List[List[bool]]] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.tilewidth = tilewidth
        self.tileheight = tileheight
        self.tile_layers = tile_layers
        # Default to all False if none provided
        self.collision_mask: List[List[bool]] = collision_mask if collision_mask is not None else [
            [False for _ in range(width)] for _ in range(height)
        ]

    @property
    def primary_layer(self) -> TileLayer:
        """Return the intended primary tile layer to stamp.

        If a layer named "Tiles" exists, prefer it; otherwise use the first tile layer.
        """
        for layer in self.tile_layers:
            if layer.name.lower() == "tiles":
                return layer
        return self.tile_layers[0]

    def solid_at(self, x: int, y: int) -> bool:
        return self.collision_mask[y][x]

    @classmethod
    def from_tmx(
        cls,
        path: str,
        collision_layer_names: Iterable[str] = ("collisions", "collision", "blockers", "blocks"),
    ) -> "TiledPrefab":
        """Load a Tiled TMX file and build a TiledPrefab.

        Args:
            path: Path to .tmx file.
            collision_layer_names: Object layer names considered as collision sources.

        Returns:
            TiledPrefab instance.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"TMX file not found: {path}")

        logger.debug("Loading TMX prefab from %s", path)
        tree = ET.parse(path)
        root = tree.getroot()

        # Validate map type
        orientation = root.attrib.get("orientation", "orthogonal")
        if orientation != "orthogonal":
            raise ValueError(f"Only orthogonal maps are supported, got orientation={orientation}")

        width = int(root.attrib["width"])
        height = int(root.attrib["height"])
        tilewidth = int(root.attrib["tilewidth"]) if "tilewidth" in root.attrib else 1
        tileheight = int(root.attrib["tileheight"]) if "tileheight" in root.attrib else 1

        # Parse tile layers (CSV only)
        tile_layers: List[TileLayer] = []
        for layer_el in root.findall("layer"):
            name = layer_el.attrib.get("name", "Layer")
            lwidth = int(layer_el.attrib.get("width", width))
            lheight = int(layer_el.attrib.get("height", height))
            if lwidth != width or lheight != height:
                raise ValueError(
                    f"Layer {name!r} has size {lwidth}x{lheight} not matching map {width}x{height}"
                )
            data_el = layer_el.find("data")
            if data_el is None:
                raise ValueError(f"Layer {name!r} has no <data>")
            encoding = data_el.attrib.get("encoding", "")
            if encoding != "csv":
                raise ValueError(
                    f"Layer {name!r} data encoding={encoding!r} is unsupported (only 'csv' is supported)"
                )
            # Normalize and parse CSV; allow newlines and trailing commas
            raw = (data_el.text or "").replace("\n", ",").replace("\r", ",")
            parts = [p.strip() for p in raw.split(",")]
            nums = [int(p) for p in parts if p != ""]
            if len(nums) != width * height:
                raise ValueError(
                    f"Layer {name!r} has {len(nums)} gids but expected {width * height} (width*height)"
                )
            # Build 2D grid [y][x]
            grid: List[List[int]] = []
            it = iter(nums)
            for _row in range(height):
                row: List[int] = []
                for _col in range(width):
                    row.append(next(it))
                grid.append(row)
            tile_layers.append(TileLayer(name=name, width=width, height=height, data=grid))

        if not tile_layers:
            raise ValueError("TMX must contain at least one tile layer")

        # Parse collisions from object groups with accepted names
        collision_mask: List[List[bool]] = [[False for _ in range(width)] for _ in range(height)]
        lower_names = {n.lower() for n in collision_layer_names}
        for og_el in root.findall("objectgroup"):
            og_name = og_el.attrib.get("name", "").lower()
            if og_name not in lower_names:
                continue
            for obj in og_el.findall("object"):
                # Only rectangle objects are supported (polygon/polyline will be ignored)
                # Tiled rectangle objects have width/height attributes and no 'polygon' child.
                if obj.find("polygon") is not None or obj.find("polyline") is not None:
                    logger.warning("Ignoring non-rect collision object in layer %s", og_name)
                    continue
                x = float(obj.attrib.get("x", "0"))
                y = float(obj.attrib.get("y", "0"))
                w = float(obj.attrib.get("width", "0"))
                h = float(obj.attrib.get("height", "0"))
                # Convert pixel coords to tile coords (rounding down)
                tx0 = int(x // tilewidth)
                ty0 = int(y // tileheight)
                tx1 = int((x + w - 1e-6) // tilewidth)
                ty1 = int((y + h - 1e-6) // tileheight)
                for ty in range(max(0, ty0), min(height, ty1 + 1)):
                    for tx in range(max(0, tx0), min(width, tx1 + 1)):
                        collision_mask[ty][tx] = True

        return cls(
            width=width,
            height=height,
            tilewidth=tilewidth,
            tileheight=tileheight,
            tile_layers=tile_layers,
            collision_mask=collision_mask,
        )


@dataclass
class StampOptions:
    """Options controlling prefab stamping behavior."""

    respect_collisions: bool = True  # Prevent stamping if any collision overlap
    apply_collisions: bool = True    # Write prefab collision mask into target map
    overwrite_tiles: bool = True     # Replace target tiles with non-zero prefab tiles


class PrefabStamper:
    """Applies TiledPrefab instances into a MapAdapter grid."""

    @staticmethod
    def can_stamp(
        target: MapAdapter,
        prefab: TiledPrefab,
        dest_x: int,
        dest_y: int,
        options: Optional[StampOptions] = None,
    ) -> bool:
        """Check whether the prefab can be stamped at the given location.

        Validates bounds and (optionally) collision overlaps.
        """
        if options is None:
            options = StampOptions()

        tw, th = target.get_size()
        # Bounds check
        if dest_x < 0 or dest_y < 0:
            return False
        if dest_x + prefab.width > tw or dest_y + prefab.height > th:
            return False

        if not options.respect_collisions:
            return True

        # Collision overlap: if any tile in prefab with solid collision would overlap a blocked tile
        for py in range(prefab.height):
            for px in range(prefab.width):
                # Only consider cells that will affect the map: either have a tile or a collision
                has_tile = prefab.primary_layer.gid_at(px, py) != 0
                has_coll = prefab.solid_at(px, py)
                if not (has_tile or has_coll):
                    continue
                tx = dest_x + px
                ty = dest_y + py
                if target.is_blocked(tx, ty):
                    return False
        return True

    @staticmethod
    def stamp(
        target: MapAdapter,
        prefab: TiledPrefab,
        dest_x: int,
        dest_y: int,
        options: Optional[StampOptions] = None,
    ) -> bool:
        """Stamp the prefab into the target map at top-left (dest_x, dest_y).

        Returns True if stamping succeeded; False if blocked by collisions or bounds when
        respect_collisions is enabled. No partial writes occur on failure.
        """
        if options is None:
            options = StampOptions()

        if not PrefabStamper.can_stamp(target, prefab, dest_x, dest_y, options):
            logger.info("Prefab cannot be stamped at %s,%s due to bounds/collision", dest_x, dest_y)
            return False

        # Apply tiles and collisions. To avoid partial writes in case of unexpected errors,
        # we accumulate intended writes then apply.
        writes_tiles: List[Tuple[int, int, int]] = []  # (x, y, gid)
        writes_blocks: List[Tuple[int, int, bool]] = []

        layer = prefab.primary_layer
        for py in range(prefab.height):
            for px in range(prefab.width):
                gid = layer.gid_at(px, py)
                if gid != 0 and options.overwrite_tiles:
                    writes_tiles.append((dest_x + px, dest_y + py, gid))
                if options.apply_collisions and prefab.solid_at(px, py):
                    writes_blocks.append((dest_x + px, dest_y + py, True))

        # Apply writes
        try:
            for (x, y, gid) in writes_tiles:
                target.set_tile(x, y, gid)
            for (x, y, blocked) in writes_blocks:
                target.set_blocked(x, y, blocked)
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Failed stamping prefab: %s", e)
            return False

        return True


__all__ = [
    "TiledPrefab",
    "TileLayer",
    "MapAdapter",
    "GridMap",
    "StampOptions",
    "PrefabStamper",
]
