from __future__ import annotations

import logging
from typing import Optional, Tuple

try:
    import arcade
except Exception as exc:  # pragma: no cover - will be covered by tests using stub
    # Defer import errors until runtime in case tests/stubs inject arcade
    arcade = None  # type: ignore


LOGGER = logging.getLogger(__name__)

# Window constants
TITLE: str = "Amor Mortuorum"
DEFAULT_WIDTH: int = 1280
DEFAULT_HEIGHT: int = 720
# Base background color (dark, near-black): RGB
BASE_BG_COLOR: Tuple[int, int, int] = (11, 13, 18)


class GameWindow(arcade.Window):
    """Primary application window.

    Handles basic drawing and resizes while maintaining a sane viewport mapping.
    """

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        title: str = TITLE,
        resizable: bool = True,
        background_color: Tuple[int, int, int] = BASE_BG_COLOR,
    ) -> None:
        # Important: pass title and resizable to parent class
        super().__init__(width=width, height=height, title=title, resizable=resizable)
        self._background_color = background_color
        # Set background color for clear() operations
        arcade.set_background_color(self._background_color)
        LOGGER.debug(
            "Initialized GameWindow: %dx%d, title='%s', resizable=%s",
            width,
            height,
            title,
            resizable,
        )

    # Arcade lifecycle hooks
    def on_draw(self) -> None:  # pragma: no cover - trivial drawing call
        # Clear the window to the background color
        self.clear()
        # Future: draw UI, scenes, etc.

    def on_resize(self, width: float, height: float) -> None:
        """Handle window resizing by updating the viewport.

        A "sane" viewport maps logical coordinates directly to the current window
        size so that drawing at pixel coordinates remains consistent after a
        resize.
        """
        try:
            super().on_resize(width, height)
        except Exception:  # super may be a stub in tests
            pass

        # Map (0,0) bottom-left to (width, height) top-right
        # Using exact ints to avoid jitter/float rounding issues.
        left = 0
        right = int(width)
        bottom = 0
        top = int(height)
        arcade.set_viewport(left, right, bottom, top)
        LOGGER.debug(
            "Viewport updated on resize: left=%d, right=%d, bottom=%d, top=%d",
            left,
            right,
            bottom,
            top,
        )


def create_window(
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    *,
    title: str = TITLE,
    resizable: bool = True,
    background_color: Tuple[int, int, int] = BASE_BG_COLOR,
) -> GameWindow:
    """Factory to create and return the game window.

    Separated for testability; does not start the app loop.
    """
    if arcade is None:  # pragma: no cover - protective guard
        raise RuntimeError("Arcade is not available; cannot create a window.")

    window = GameWindow(
        width=width,
        height=height,
        title=title,
        resizable=resizable,
        background_color=background_color,
    )
    return window


def main(argv: Optional[list[str]] = None) -> int:
    """Module entrypoint: create window and start Arcade event loop.

    Args:
        argv: Optional command-line arguments (unused).

    Returns:
        Process exit code (0 on success).
    """
    # Lightweight logging configuration; applications can override as needed
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    LOGGER.info("Starting Amor Mortuorum")

    try:
        create_window()
        arcade.run()
        return 0
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        LOGGER.exception("Unhandled exception in game loop: %s", exc)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
