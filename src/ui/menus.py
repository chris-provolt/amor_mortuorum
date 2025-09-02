from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MenuItem:
    """A single menu item.

    Attributes:
        id: Stable identifier for the item (used by logic).
        label: Human-friendly text displayed in the UI.
        enabled: If False, the item is skipped during navigation and cannot be selected.
    """
    id: str
    label: str
    enabled: bool = True


class VerticalMenu:
    """Engine-agnostic vertical menu model with input commands.

    This class contains no rendering or framework-specific logic. It exposes a simple
    command interface for navigation and activation that a scene/view can map to
    engine-specific key inputs.
    """

    def __init__(
        self,
        items: Iterable[MenuItem],
        *,
        selected_index: int = 0,
        wrap_navigation: bool = True,
        on_activate: Optional[Callable[[MenuItem], None]] = None,
    ) -> None:
        self._items: List[MenuItem] = list(items)
        if not self._items:
            raise ValueError("VerticalMenu requires at least one MenuItem")
        self._selected_index: int = max(0, min(selected_index, len(self._items) - 1))
        self._wrap = wrap_navigation
        self._on_activate = on_activate

    @property
    def items(self) -> List[MenuItem]:
        return self._items

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def selected_item(self) -> MenuItem:
        return self._items[self._selected_index]

    def set_on_activate(self, handler: Optional[Callable[[MenuItem], None]]) -> None:
        self._on_activate = handler

    def _move(self, delta: int) -> None:
        """Move selection by delta, skipping disabled items.

        If wrap_navigation is False and an edge is reached, selection remains.
        """
        if delta == 0:
            return
        count = len(self._items)
        next_index = self._selected_index
        attempts = 0
        while attempts < count:
            next_index = next_index + delta
            if self._wrap:
                next_index %= count
            else:
                if next_index < 0 or next_index >= count:
                    # Can't move past edges without wrapping
                    return
            if self._items[next_index].enabled:
                self._selected_index = next_index
                return
            attempts += 1
        # If all items are disabled, do nothing
        logger.debug("VerticalMenu._move: all items disabled or no valid move; selection unchanged")

    def move_up(self) -> None:
        self._move(-1)

    def move_down(self) -> None:
        self._move(1)

    def activate(self) -> MenuItem:
        item = self.selected_item
        if not item.enabled:
            logger.debug("VerticalMenu.activate: selected item is disabled: %s", item)
            return item
        if self._on_activate:
            try:
                self._on_activate(item)
            except Exception:
                logger.exception("Error during menu activation for item: %s", item)
        return item

    def input(self, command: str) -> Optional[MenuItem]:
        """Process a high-level input command.

        Supported commands: 'up', 'down', 'select'.
        Returns the activated MenuItem for 'select', otherwise None.
        """
        cmd = command.lower().strip()
        if cmd in ("up", "prev", "previous"):
            self.move_up()
            return None
        if cmd in ("down", "next"):
            self.move_down()
            return None
        if cmd in ("select", "enter", "activate"):
            return self.activate()
        raise ValueError(f"Unsupported command: {command}")

    def get_draw_model(
        self,
        x: float,
        y: float,
        line_height: float,
        *,
        center_x: bool = True,
    ) -> List[dict]:
        """Return a simple draw model that a renderer can consume.

        Each entry: { 'text': str, 'x': float, 'y': float, 'selected': bool, 'enabled': bool }
        """
        rows: List[dict] = []
        cur_y = y
        for idx, m in enumerate(self._items):
            rows.append(
                {
                    "text": m.label,
                    "x": x,
                    "y": cur_y,
                    "selected": idx == self._selected_index,
                    "enabled": m.enabled,
                    "center_x": center_x,
                }
            )
            cur_y -= line_height
        return rows
