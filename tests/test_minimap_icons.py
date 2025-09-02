import pytest

from amormortuorum.minimap import (
    FeatureType,
    MinimapIconService,
    MinimapIconRegistry,
    UnknownFeatureError,
    DiscoveryAmbiguityError,
)


def make_service() -> MinimapIconService:
    return MinimapIconService(MinimapIconRegistry())


def test_icons_appear_only_after_discovery_and_exploration():
    svc = make_service()
    pos = (3, 4)
    svc.register_feature(FeatureType.STAIRS, pos)

    # Not discovered yet: should not show
    icons = svc.get_visible_icons(explored={pos})
    assert icons == []

    # Discovered but not explored: should not show
    svc.discover_feature(FeatureType.STAIRS, pos)
    icons = svc.get_visible_icons(explored=set())
    assert icons == []

    # Discovered and explored: should show
    icons = svc.get_visible_icons(explored={pos})
    assert len(icons) == 1
    assert icons[0].feature_type == FeatureType.STAIRS
    assert icons[0].position == pos


def test_discover_by_position_and_ambiguity():
    svc = make_service()
    pos = (1, 1)
    svc.register_feature(FeatureType.CHEST, pos)

    discovered_type = svc.discover_feature_at(pos)
    assert discovered_type == FeatureType.CHEST

    # Ambiguity protection
    other = (2, 2)
    svc.register_feature(FeatureType.CHEST, other)
    svc.register_feature(FeatureType.BOSS, other)
    with pytest.raises(DiscoveryAmbiguityError):
        svc.discover_feature_at(other)


def test_remove_feature_hides_icon_but_keeps_legend():
    svc = make_service()
    pos = (5, 5)
    svc.register_feature(FeatureType.CHEST, pos)
    # Discover and explore
    svc.discover_feature(FeatureType.CHEST, pos)

    # Visible when explored
    icons = svc.get_visible_icons(explored={pos})
    assert len(icons) == 1
    assert icons[0].feature_type == FeatureType.CHEST

    # Remove feature (e.g., opened chest) => no icon anymore
    svc.remove_feature(pos)
    icons = svc.get_visible_icons(explored={pos})
    assert icons == []

    # Legend still shows chest since it was discovered this floor
    legend = svc.get_legend()
    labels = [d.label for d in legend]
    assert "Chest" in labels


def test_legend_consistency_and_ordering():
    svc = make_service()
    # Register and discover multiple types
    svc.register_feature(FeatureType.BOSS, (0, 0))
    svc.register_feature(FeatureType.STAIRS, (1, 1))

    svc.discover_feature(FeatureType.STAIRS, (1, 1))
    svc.discover_feature(FeatureType.BOSS, (0, 0))

    legend = svc.get_legend()
    # Expected order by FeatureType enum definition: STAIRS, CHEST, BOSS; only discovered entries appear
    assert [d.feature_type for d in legend] == [FeatureType.STAIRS, FeatureType.BOSS]

    # Descriptor consistency
    stairs_desc = next(d for d in legend if d.feature_type == FeatureType.STAIRS)
    assert stairs_desc.label == "Stairs"
    assert stairs_desc.glyph == ">"


def test_explored_grid_variants():
    svc = make_service()
    pos = (2, 1)
    svc.register_feature(FeatureType.BOSS, pos)
    svc.discover_feature(FeatureType.BOSS, pos)

    # 2D boolean grid explored[y][x]
    grid = [
        [False, False, False],
        [False, False, True],
    ]
    icons = svc.get_visible_icons(explored=grid)
    assert len(icons) == 1
    assert icons[0].position == pos

    # Callable predicate
    icons = svc.get_visible_icons(explored=lambda x, y: (x, y) == pos)
    assert len(icons) == 1
    assert icons[0].feature_type == FeatureType.BOSS


def test_clearing_floor_resets_discoveries():
    svc = make_service()
    pos = (7, 7)

    svc.register_feature(FeatureType.STAIRS, pos)
    svc.discover_feature(FeatureType.STAIRS, pos)

    assert svc.get_legend()  # Non-empty

    svc.clear_floor()

    # After clearing, legend is empty and no active/discovered icons remain
    assert svc.get_legend() == []
    assert svc.get_visible_icons(explored={pos}) == []
