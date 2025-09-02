from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple


logger = logging.getLogger(__name__)


class MinimapError(Exception):
    """Base exception for minimap icon operations."""


class UnknownFeatureError(MinimapError):
    """Raised when attempting to use an unknown feature type or position."""


class DiscoveryAmbiguityError(MinimapError):
    """Raised when discovery by position is ambiguous across multiple feature types."""


class FeatureType(str, Enum):
    """Enumeration of minimap feature types supported by the system.

    Extensible in the future (e.g., portal, traps, merchants), but this task
    focuses on STAIRS, CHEST, and BOSS.
    """

    STAIRS = "stairs"
    CHEST = "chest"
    BOSS = "boss"


@dataclass(frozen=True)
class MinimapIconDescriptor:
    """Describes how a feature type should appear in the minimap legend.

    - label: user-facing name shown in the legend
    - glyph: a single-character or short text symbol (fallback when no texture)
    - color: RGB tuple for tinting or UI rendering
    - texture_key: optional key/path if a rendering system uses textures
    """

    feature_type: FeatureType
    label: str
    glyph: str
    color: Tuple[int, int, int]
    texture_key: Optional[str] = None


@dataclass(frozen=True)
class MinimapIcon:
    """A concrete icon to render on the minimap at a specific map position."""

    feature_type: FeatureType
    position: Tuple[int, int]
    glyph: str
    label: str
    color: Tuple[int, int, int]
    texture_key: Optional[str] = None


class MinimapIconRegistry:
    """Registry that maps FeatureType to a stable, consistent descriptor.

    The registry ensures the legend remains consistent across sessions and
    systems by providing a stable mapping for labels/glyphs/colors.
    """

    def __init__(self, descriptors: Optional[Iterable[MinimapIconDescriptor]] = None) -> None:
        if descriptors is None:
            descriptors = self._default_descriptors()
        self._map: Dict[FeatureType, MinimapIconDescriptor] = {d.feature_type: d for d in descriptors}
        # Validate uniqueness and completeness for the supported features
        for ft in (FeatureType.STAIRS, FeatureType.CHEST, FeatureType.BOSS):
            if ft not in self._map:
                raise ValueError(f"Descriptor for feature type '{ft}' not provided")

    @staticmethod
    def _default_descriptors() -> List[MinimapIconDescriptor]:
        # Reasonable default glyph and color scheme. Colors are UI hints only.
        return [
            MinimapIconDescriptor(
                feature_type=FeatureType.STAIRS, label="Stairs", glyph=">", color=(180, 180, 255), texture_key="stairs_icon"
            ),
            MinimapIconDescriptor(
                feature_type=FeatureType.CHEST, label="Chest", glyph="C", color=(255, 215, 0), texture_key="chest_icon"
            ),
            MinimapIconDescriptor(
                feature_type=FeatureType.BOSS, label="Boss Gate", glyph="B", color=(255, 80, 80), texture_key="boss_icon"
            ),
        ]

    def get(self, feature_type: FeatureType) -> MinimapIconDescriptor:
        try:
            return self._map[feature_type]
        except KeyError as exc:
            raise UnknownFeatureError(f"No descriptor registered for feature type: {feature_type}") from exc

    def legend_for(self, feature_types: Iterable[FeatureType]) -> List[MinimapIconDescriptor]:
        # Keep stable ordering by enum definition order
        order = {ft: i for i, ft in enumerate(FeatureType)}
        unique: List[MinimapIconDescriptor] = []
        seen: Set[FeatureType] = set()
        for ft in sorted(set(feature_types), key=lambda x: order[x]):
            if ft not in seen:
                unique.append(self.get(ft))
                seen.add(ft)
        return unique


class MinimapIconService:
    """Service that manages discovery and visibility of minimap icons.

    Responsibilities:
    - Maintain set of present (registered) features on the floor
    - Track which features/positions have been discovered by the player
    - Provide icons to render given an explored mask (Fog of War dependency)
    - Provide a stable legend for discovered feature types

    Integration points:
    - Procedural generation should call `register_feature(feature_type, pos)` for
      each feature placed on a floor (stairs, chests, boss gate).
    - When the player reveals a tile (e.g., moves adjacent, casts reveal), the
      map system should call `discover_feature_at(pos)` to mark it discovered.
      Alternatively, call `discover_feature(feature_type, pos)` if type is known.
    - When a feature is consumed/removed (e.g., chest opened), call `remove_feature(pos)`.
    - The renderer requests `get_visible_icons(explored)` each frame/update to obtain
      the list of icons to draw, and `get_legend()` for the legend panel.
    """

    def __init__(self, registry: Optional[MinimapIconRegistry] = None) -> None:
        self.registry = registry or MinimapIconRegistry()
        # Active feature positions on the current floor
        self._active_positions_by_type: Dict[FeatureType, Set[Tuple[int, int]]] = {
            FeatureType.STAIRS: set(),
            FeatureType.CHEST: set(),
            FeatureType.BOSS: set(),
        }
        # Discovered positions - subset of active positions
        self._discovered_positions_by_type: Dict[FeatureType, Set[Tuple[int, int]]] = {
            FeatureType.STAIRS: set(),
            FeatureType.CHEST: set(),
            FeatureType.BOSS: set(),
        }
        # Once a type has been discovered at least once, it enters the legend
        self._discovered_types: Set[FeatureType] = set()

    # -------------------------------
    # Feature lifecycle
    # -------------------------------
    def clear_floor(self) -> None:
        """Clear all state for the current floor (e.g., when descending)."""
        self._active_positions_by_type = {ft: set() for ft in FeatureType}
        self._discovered_positions_by_type = {ft: set() for ft in FeatureType}
        # Legend discovery is intentionally NOT cleared across floors? Typically legend visibility
        # resets per run/floor. For clarity and acceptance criteria, we reset legend per floor to ensure
        # icons appear only after discovery on that floor.
        self._discovered_types.clear()
        logger.debug("MinimapIconService floor state cleared")

    def register_feature(self, feature_type: FeatureType, position: Tuple[int, int]) -> None:
        """Register a feature as present on the floor at a given position.

        This does not mark it as discovered; it simply becomes eligible to be
        discovered when the tile is revealed.
        """
        self._validate_position(position)
        self._active_positions_by_type[feature_type].add(position)
        logger.debug("Registered feature %s at %s", feature_type, position)

    def remove_feature(self, position: Tuple[int, int]) -> None:
        """Remove a feature from active positions at the given location.

        If present in discovered positions, it will also be removed from the
        visible set. The legend of the feature type remains discovered for this floor.
        """
        self._validate_position(position)
        matched_types = [ft for ft, pos in self._active_positions_by_type.items() if position in pos]
        if not matched_types:
            logger.debug("Attempted to remove feature at %s but none was registered", position)
            return
        for ft in matched_types:
            self._active_positions_by_type[ft].discard(position)
            self._discovered_positions_by_type[ft].discard(position)
            logger.debug("Removed feature %s at %s", ft, position)

    def discover_feature(self, feature_type: FeatureType, position: Tuple[int, int]) -> None:
        """Mark a feature at the given position as discovered.

        Raises UnknownFeatureError if no such feature is registered at position.
        """
        self._validate_position(position)
        if position not in self._active_positions_by_type[feature_type]:
            raise UnknownFeatureError(
                f"No active feature of type {feature_type} at position {position} to discover"
            )
        self._discovered_positions_by_type[feature_type].add(position)
        self._discovered_types.add(feature_type)
        logger.debug("Discovered feature %s at %s", feature_type, position)

    def discover_feature_at(self, position: Tuple[int, int]) -> FeatureType:
        """Discover a feature at a given position when the type is unknown.

        If multiple feature types are registered at the same tile, raises
        DiscoveryAmbiguityError. Returns the discovered FeatureType.
        """
        self._validate_position(position)
        matched_types = [ft for ft, pos in self._active_positions_by_type.items() if position in pos]
        if not matched_types:
            raise UnknownFeatureError(f"No active feature found at {position}")
        if len(matched_types) > 1:
            # Map generator should avoid this, but guard anyway
            raise DiscoveryAmbiguityError(
                f"Multiple feature types registered at {position}: {matched_types}"
            )
        ft = matched_types[0]
        self.discover_feature(ft, position)
        return ft

    # -------------------------------
    # Visibility & Legend
    # -------------------------------
    def get_visible_icons(
        self,
        explored: Optional[object] = None,
    ) -> List[MinimapIcon]:
        """Get a list of icons to render on the minimap, respecting Fog of War.

        - explored: describes which tiles are explored/visible. It can be one of:
            * a set of (x, y) tuples
            * a 2D sequence of booleans indexed as grid[y][x]
            * a callable (x, y) -> bool
            * None, which means treat everything as explored (useful for tests)

        Icons are only returned for positions that are both:
            - discovered AND still active
            - explored according to the provided mask
        """
        visible: List[MinimapIcon] = []

        def is_explored_fn(x: int, y: int) -> bool:
            return self._is_explored((x, y), explored)

        for ft in FeatureType:
            desc = self.registry.get(ft)
            active = self._active_positions_by_type[ft]
            discovered = self._discovered_positions_by_type[ft]
            # Only show icons for tiles that are both active and discovered
            for pos in active & discovered:
                x, y = pos
                if is_explored_fn(x, y):
                    visible.append(
                        MinimapIcon(
                            feature_type=ft,
                            position=pos,
                            glyph=desc.glyph,
                            label=desc.label,
                            color=desc.color,
                            texture_key=desc.texture_key,
                        )
                    )
        # Stable sort by feature type, then position for deterministic rendering & tests
        order = {ft: i for i, ft in enumerate(FeatureType)}
        visible.sort(key=lambda ic: (order[ic.feature_type], ic.position[1], ic.position[0]))
        return visible

    def get_legend(self) -> List[MinimapIconDescriptor]:
        """Return legend entries for all feature types discovered at least once.

        The legend is stable and ordered by FeatureType enum definition order.
        """
        return self.registry.legend_for(self._discovered_types)

    # -------------------------------
    # Helpers
    # -------------------------------
    @staticmethod
    def _validate_position(position: Tuple[int, int]) -> None:
        if not isinstance(position, tuple) or len(position) != 2:
            raise ValueError("position must be a (x, y) tuple of integers")
        x, y = position
        if not (isinstance(x, int) and isinstance(y, int)):
            raise ValueError("position must contain integer coordinates")

    @staticmethod
    def _is_explored(position: Tuple[int, int], explored: Optional[object]) -> bool:
        if explored is None:
            return True
        x, y = position
        # Set of tuples
        if isinstance(explored, set):
            return (x, y) in explored
        # Callable predicate
        if callable(explored):
            try:
                return bool(explored(x, y))
            except Exception as exc:
                logger.exception("Explored predicate raised: %s", exc)
                return False
        # 2D sequence (grid[y][x])
        if isinstance(explored, Sequence) and explored:
            try:
                row = explored[y]
                return bool(row[x])
            except Exception:
                # Out of bounds or wrong shape means 'not explored'
                return False
        # Fallback: unknown model => treat as unexplored to be safe
        return False
