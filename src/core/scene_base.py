from __future__ import annotations

import logging
from typing import Optional, Tuple

import arcade

logger = logging.getLogger(__name__)


class SceneBase(arcade.View):
    """
    Base class for all game views/scenes.

    Responsibilities:
    - Viewport handling to avoid flicker on initial show and window resize.
    - Maintain separate world and UI cameras and keep them in sync with the window size.
    - Provide a utility to draw centered text on the UI layer.

    Usage:
    - Inherit this class for all views (Title, Graveyard, Dungeon, Combat, etc.)
    - Call self.ui_camera.use() to draw UI, and self.world_camera.use() to draw world.
    - Implement on_draw, on_update, input handlers in child classes as needed.

    Notes on flicker:
    - Arcade can briefly flicker during window resize if the viewport isn't updated promptly.
      This base class updates the viewport immediately in on_show_view and on_resize to
      prevent that.
    """

    def __init__(
        self,
        background_color: Tuple[int, int, int] = arcade.color.BLACK,
        default_font_name: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.background_color = background_color
        self.default_font_name = default_font_name

        # Cameras are created lazily once a window is available
        self.world_camera: Optional[arcade.Camera] = None
        self.ui_camera: Optional[arcade.Camera] = None

    # ---------------------
    # Lifecycle / Viewport
    # ---------------------
    def on_show_view(self) -> None:  # arcade callback
        """Called when this view is shown by the window.

        Ensures cameras are created and viewport is applied immediately to avoid flicker.
        """
        logger.debug("SceneBase.on_show_view()")

        # Set the background before drawing to avoid any visual tearing/flicker.
        if self.background_color is not None:
            arcade.set_background_color(self.background_color)

        # Ensure cameras exist and match the current window size
        self._ensure_cameras()

        # Ensure the viewport exactly matches the window pixel size
        self._apply_viewport()

    def on_resize(self, width: int, height: int) -> None:  # arcade callback
        """Handle window resize without flicker.

        Resizes both world and UI cameras, and reapplies the viewport so the content
        matches new dimensions.
        """
        logger.debug("SceneBase.on_resize(width=%d, height=%d)", width, height)

        # If cameras aren't created yet (edge case), create them now
        if self.world_camera is None or self.ui_camera is None:
            self._ensure_cameras()

        # Resize cameras to the new window size
        if self.world_camera is not None:
            self.world_camera.resize(width, height)
        if self.ui_camera is not None:
            self.ui_camera.resize(width, height)

        # Update viewport immediately to prevent flicker
        self._apply_viewport(width, height)

    # ---------------------
    # Drawing Helpers
    # ---------------------
    def draw_centered_text(
        self,
        text: str,
        *,
        center_x: Optional[float] = None,
        center_y: Optional[float] = None,
        font_size: float = 24,
        color: Tuple[int, int, int] = arcade.color.WHITE,
        font_name: Optional[str] = None,
        bold: bool = False,
    ) -> None:
        """Draw text centered at the given UI position (or screen center by default).

        By default, draws to the UI space, so call self.ui_camera.use() beforehand
        if you are switching between world and UI drawing.
        """
        win = self.window
        if win is None:
            raise RuntimeError("SceneBase.draw_centered_text called before window is set.")

        cx = center_x if center_x is not None else win.width / 2
        cy = center_y if center_y is not None else win.height / 2

        arcade.draw_text(
            text,
            cx,
            cy,
            color=color,
            font_size=font_size,
            font_name=font_name or self.default_font_name,
            anchor_x="center",
            anchor_y="center",
            bold=bold,
        )

    # ---------------------
    # Convenience API
    # ---------------------
    @property
    def size(self) -> Tuple[int, int]:
        """Return current window size as (width, height)."""
        if self.window is None:
            return 0, 0
        return int(self.window.width), int(self.window.height)

    def use_world(self) -> None:
        """Activate the world camera for world-space drawing."""
        self._ensure_cameras()
        assert self.world_camera is not None
        self.world_camera.use()

    def use_ui(self) -> None:
        """Activate the UI camera for screen-space drawing."""
        self._ensure_cameras()
        assert self.ui_camera is not None
        self.ui_camera.use()

    # ---------------------
    # Internal Utilities
    # ---------------------
    def _ensure_cameras(self) -> None:
        """Create cameras if they don't exist yet, using the current window size."""
        win = self.window
        if win is None:
            # When running tests or before the view is shown, window can be None.
            # Defer camera creation until a window is available.
            logger.debug("_ensure_cameras skipped: window is None")
            return

        if self.world_camera is None:
            logger.debug("Creating world_camera with size (%d, %d)", win.width, win.height)
            self.world_camera = arcade.Camera(win.width, win.height)
        if self.ui_camera is None:
            logger.debug("Creating ui_camera with size (%d, %d)", win.width, win.height)
            self.ui_camera = arcade.Camera(win.width, win.height)

    def _apply_viewport(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Apply a pixel-perfect viewport matching the window size.

        Explicitly setting the viewport on show and resize prevents resize flicker.
        """
        win = self.window
        if win is None:
            logger.debug("_apply_viewport skipped: window is None")
            return

        w = int(width if width is not None else win.width)
        h = int(height if height is not None else win.height)
        # Arcade expects left, right, bottom, top in window coordinates
        arcade.set_viewport(0, w, 0, h)
        logger.debug("Viewport applied: left=0 right=%d bottom=0 top=%d", w, h)
