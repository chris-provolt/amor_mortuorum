"""Vertical menu: a pure-Python selection model plus an arcade view.

``VerticalMenu`` holds items and the cursor and maps input actions to moves; it
has no arcade dependency and is unit-tested. ``MenuView`` renders one with
cached ``arcade.Text`` objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence


@dataclass
class MenuItem:
    label: str
    action: Optional[Callable[[], Any]] = None
    enabled: bool = True
    hint: str = ""
    payload: Any = None
    extra: dict = field(default_factory=dict)


class VerticalMenu:
    """Cursor over a list of items. Disabled items are skipped by the cursor."""

    def __init__(self, items: Sequence[MenuItem] = (), *, wrap: bool = True) -> None:
        self.items: List[MenuItem] = list(items)
        self.wrap = wrap
        self.selected: int = 0
        self._snap_to_enabled(+1)

    # Items

    def set_items(self, items: Sequence[MenuItem], keep_selection: bool = True) -> None:
        old = self.selected
        self.items = list(items)
        self.selected = min(old, len(self.items) - 1) if keep_selection and self.items else 0
        self._snap_to_enabled(+1)

    @property
    def current(self) -> Optional[MenuItem]:
        if not self.items:
            return None
        return self.items[self.selected]

    def __len__(self) -> int:
        return len(self.items)

    # Cursor

    def _snap_to_enabled(self, direction: int) -> None:
        if not self.items or self.items[self.selected].enabled:
            return
        for _ in range(len(self.items)):
            self.selected = (self.selected + direction) % len(self.items)
            if self.items[self.selected].enabled:
                return

    def move(self, delta: int) -> int:
        """Move the cursor by ``delta`` rows, skipping disabled items. Returns the new index."""
        if not self.items or delta == 0:
            return self.selected
        step = 1 if delta > 0 else -1
        n = len(self.items)
        for _ in range(abs(delta)):
            idx = self.selected
            for _ in range(n):
                nxt = idx + step
                if not self.wrap and not 0 <= nxt < n:
                    break
                idx = nxt % n
                if self.items[idx].enabled:
                    self.selected = idx
                    break
        return self.selected

    def activate(self) -> bool:
        """Run the selected item's action. Returns False if nothing could be activated."""
        item = self.current
        if item is None or not item.enabled:
            return False
        if item.action is not None:
            item.action()
        return True

    # Input mapping

    def handle_actions(self, actions: Sequence[str]) -> bool:
        """Apply input actions (``move_up``/``move_down``/``confirm``). Returns handled."""
        handled = False
        if "move_up" in actions:
            self.move(-1)
            handled = True
        if "move_down" in actions:
            self.move(+1)
            handled = True
        if "confirm" in actions:
            self.activate()
            handled = True
        return handled


class MenuView:
    """Renders a ``VerticalMenu`` with one cached ``arcade.Text`` per row."""

    def __init__(
        self,
        menu: VerticalMenu,
        x: float,
        y: float,
        *,
        font_size: int = 20,
        spacing: Optional[float] = None,
        anchor_x: str = "left",
        color=(220, 220, 230),
        selected_color=(255, 215, 120),
        disabled_color=(110, 110, 120),
        cursor: str = "> ",
    ) -> None:
        import arcade  # local import keeps the module importable without a window

        self._arcade = arcade
        self.menu = menu
        self.x = x
        self.y = y
        self.font_size = font_size
        self.spacing = spacing if spacing is not None else font_size * 1.6
        self.anchor_x = anchor_x
        self.color = color
        self.selected_color = selected_color
        self.disabled_color = disabled_color
        self.cursor = cursor
        self._rows: List[Any] = []
        self._hint = arcade.Text(
            "", x, y, color=disabled_color, font_size=max(10, font_size - 6), anchor_x=anchor_x
        )
        self.rebuild()

    def set_position(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self._layout()

    def rebuild(self) -> None:
        arcade = self._arcade
        self._rows = [
            arcade.Text("", self.x, self.y, font_size=self.font_size, anchor_x=self.anchor_x)
            for _ in self.menu.items
        ]
        self._layout()

    def _layout(self) -> None:
        for i, row in enumerate(self._rows):
            row.position = (self.x, self.y - i * self.spacing)
        self._hint.position = (self.x, self.y - len(self._rows) * self.spacing - self.spacing * 0.4)

    def draw(self) -> None:
        if len(self._rows) != len(self.menu.items):
            self.rebuild()
        pad = " " * len(self.cursor)
        for i, (row, item) in enumerate(zip(self._rows, self.menu.items)):
            selected = i == self.menu.selected
            prefix = self.cursor if selected else pad
            text = prefix + item.label
            if row.text != text:
                row.text = text
            color = (
                self.disabled_color
                if not item.enabled
                else self.selected_color if selected else self.color
            )
            if row.color != color:
                row.color = color
            row.draw()
        current = self.menu.current
        hint = current.hint if current else ""
        if self._hint.text != hint:
            self._hint.text = hint
        if hint:
            self._hint.draw()
