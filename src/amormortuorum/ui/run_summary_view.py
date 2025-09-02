from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from amormortuorum.core.navigation import NextAction
from amormortuorum.domain.run_summary import RunSummary

logger = logging.getLogger(__name__)


class RunSummaryController:
    """Controller for Run Summary interactions.

    UI toolkits (Arcade, terminal, etc.) can delegate key events to this
    controller to get the NextAction.
    """

    def __init__(self, summary: RunSummary, on_complete: Optional[Callable[[NextAction], None]] = None):
        self.summary = summary
        self.on_complete = on_complete

    def default_action(self) -> NextAction:
        # For now, default is to go to Graveyard regardless of outcome.
        # Adjust in the future if certain outcomes prefer Main Menu.
        return NextAction.TO_GRAVEYARD

    def handle_key(self, key: str) -> Optional[NextAction]:
        """Handle a key identifier and return the chosen action if any.

        Expected keys:
        - 'enter', 'space', 'g' -> Graveyard
        - 'm' -> Main Menu
        Unknown keys return None.
        """
        k = (key or "").lower()
        if k in ("enter", "return", "space", "g"):
            action = NextAction.TO_GRAVEYARD
        elif k == "m":
            action = NextAction.TO_MAIN_MENU
        else:
            logger.debug("Unhandled key on RunSummaryController: %s", key)
            return None
        if self.on_complete:
            try:
                self.on_complete(action)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("on_complete callback raised an exception")
        return action

    def summary_lines(self, width: int = 80) -> Sequence[str]:
        return self.summary.format_lines(width=width)


# Optional Arcade view (gracefully degrades if Arcade is not installed).
try:
    import arcade
except Exception:  # pragma: no cover - if arcade is unavailable in tests/CI
    arcade = None  # type: ignore


class ArcadeRunSummaryView:  # not a direct arcade.View to keep import-optional
    """Arcade-backed Run Summary screen.

    Use within Arcade application if arcade is available. This class wraps an
    arcade.View internally to avoid import errors when Arcade isn't installed.
    """

    def __init__(self, summary: RunSummary, on_complete: Callable[[NextAction], None]):
        self.summary = summary
        self.on_complete = on_complete
        self._view: Optional["_InternalArcadeView"] = None
        if arcade is not None:
            self._view = _InternalArcadeView(summary, on_complete)
        else:
            logger.warning("Arcade is not installed; ArcadeRunSummaryView is inactive")

    @property
    def view(self):
        """Return the underlying arcade.View (or None if unavailable)."""
        return self._view


if arcade is not None:  # pragma: no cover - requires arcade & window

    class _InternalArcadeView(arcade.View):
        PADDING = 20

        def __init__(self, summary: RunSummary, on_complete: Callable[[NextAction], None]):
            super().__init__()
            self.controller = RunSummaryController(summary, on_complete)
            self.lines = list(self.controller.summary_lines(width=80))

        def on_draw(self):
            self.clear()
            width, height = self.window.get_size()
            y = height - self.PADDING
            for i, line in enumerate(self.lines):
                # Larger font for title lines
                font_size = 28 if i == 0 else (20 if i == 1 else 16)
                arcade.draw_text(
                    line,
                    self.PADDING,
                    y - (i * (font_size + 8)),
                    arcade.color.WHITE,
                    font_size,
                )

        def on_key_press(self, symbol: int, modifiers: int):
            # Map arcade key codes to controller keys
            key_map = {
                arcade.key.ENTER: "enter",
                arcade.key.RETURN: "return",
                arcade.key.SPACE: "space",
                arcade.key.G: "g",
                arcade.key.M: "m",
            }
            key = key_map.get(symbol)
            if key:
                action = self.controller.handle_key(key)
                if action is not None:
                    # Delegate navigation to caller via callback
                    # Caller should switch views based on action
                    pass

        def on_show_view(self):
            arcade.set_background_color(arcade.color.BLACK)
