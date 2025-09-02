from dataclasses import dataclass


@dataclass(frozen=True)
class MinimapConfig:
    """Runtime configuration for the minimap.

    Fractions are proportions of the current window size.
    """

    # How much of the window the minimap can occupy
    max_width_fraction: float = 0.22
    max_height_fraction: float = 0.30

    # Margins from window edges (in pixels)
    margin_px: int = 12

    # Colors (RGBA)
    background_color: tuple[int, int, int, int] = (10, 10, 14, 200)
    border_color: tuple[int, int, int, int] = (70, 70, 80, 220)
    explored_color: tuple[int, int, int, int] = (120, 160, 200, 240)
    player_color: tuple[int, int, int, int] = (255, 255, 255, 255)


@dataclass(frozen=True)
class WorldConfig:
    # Logical map size (tiles)
    width: int = 48
    height: int = 48

    # World rendering tile size (for the main view, not the minimap)
    tile_px: int = 24


MINIMAP = MinimapConfig()
WORLD = WorldConfig()
