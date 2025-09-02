from __future__ import annotations

import logging
from typing import Optional

import importlib

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover - tests may stub arcade
    arcade = None  # type: ignore

from ui.menus import VerticalMenu, MenuItem

logger = logging.getLogger(__name__)


TITLE = "Graveyard"
TITLE_COLOR = (235, 235, 235)
MENU_COLOR = (210, 210, 210)
MENU_DISABLED_COLOR = (130, 130, 130)
MENU_HIGHLIGHT_COLOR = (255, 240, 180)
BG_COLOR = (20, 20, 24)

TITLE_FONT_SIZE = 36
MENU_FONT_SIZE = 20
LINE_HEIGHT = 28


class GraveyardView(getattr(__import__(__name__), 'arcade', type('A', (), {'View': object})).View):
    """Graveyard hub scene with a vertical menu.

    Menu options: Enter / Rest / Crypt / Purchase / Quit.
    - Up/Down to navigate, Enter/Space to activate.
    - Selecting Enter transitions to the Dungeon at floor 1.
    """

    def __init__(self) -> None:
        try:
            super().__init__()
        except Exception:
            # When arcade is stubbed, super may not be callable; ignore
            pass

        self.menu = VerticalMenu(
            [
                MenuItem("enter", "Enter"),
                MenuItem("rest", "Rest"),
                MenuItem("crypt", "Crypt"),
                MenuItem("purchase", "Purchase"),
                MenuItem("quit", "Quit"),
            ]
        )
        self.menu.set_on_activate(self._on_menu_activate)
        self._status_message: Optional[str] = None

    def on_show_view(self) -> None:  # pragma: no cover - visual
        if arcade:
            arcade.set_background_color(BG_COLOR)
        self._status_message = None
        logger.info("Showing Graveyard view")

    # Input handling
    def _arcade_key_to_command(self, symbol: int) -> Optional[str]:
        if not arcade:  # Shouldn't happen during runtime, only tests
            return None
        k = arcade.key
        if symbol in (getattr(k, 'UP', -1), getattr(k, 'W', -2)):
            return 'up'
        if symbol in (getattr(k, 'DOWN', -1), getattr(k, 'S', -2)):
            return 'down'
        if symbol in (getattr(k, 'ENTER', -1), getattr(k, 'RETURN', -2), getattr(k, 'SPACE', -3)):
            return 'select'
        return None

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        try:
            cmd = self._arcade_key_to_command(symbol) if arcade else None
        except Exception:
            cmd = None
        if not cmd:
            return
        result = self.menu.input(cmd)
        if result is not None:
            # Activation handled by menu's on_activate callback
            pass

    def _on_menu_activate(self, item: MenuItem) -> None:
        logger.debug("Menu activate: %s", item)
        if item.id == 'enter':
            self._go_to_dungeon(1)
        elif item.id == 'quit':
            try:
                if getattr(self, 'window', None) is not None:
                    self.window.close()  # type: ignore[attr-defined]
            except Exception:
                logger.exception("Failed to close window on Quit")
        elif item.id == 'rest':
            self._status_message = "You rest and feel renewed."
            logger.info("Rest selected at Graveyard")
        elif item.id == 'crypt':
            self._status_message = "The Crypt is not implemented yet."
            logger.info("Crypt selected (TODO)")
        elif item.id == 'purchase':
            self._status_message = "The shop is not implemented yet."
            logger.info("Purchase selected (TODO)")

    def _go_to_dungeon(self, floor: int) -> None:
        """Transition to the Dungeon scene.

        Attempts to import scenes.dungeon.DungeonView and instantiate it.
        """
        dungeon_view = None
        try:
            module = importlib.import_module('scenes.dungeon')
            DungeonView = getattr(module, 'DungeonView')
            dungeon_view = DungeonView(start_floor=floor)
        except Exception as e:
            logger.exception("Failed to import/instantiate DungeonView: %s", e)
            return
        try:
            if getattr(self, 'window', None) is not None:
                self.window.show_view(dungeon_view)  # type: ignore[attr-defined]
            else:
                logger.warning("No window bound to view; cannot transition to dungeon.")
        except Exception:
            logger.exception("Failed to show DungeonView")

    # Rendering
    def on_draw(self) -> None:  # pragma: no cover - visual
        if not arcade:
            return
        arcade.start_render()

        # Title
        width = self.window.width if getattr(self, 'window', None) is not None else 800  # type: ignore[attr-defined]
        height = self.window.height if getattr(self, 'window', None) is not None else 600  # type: ignore[attr-defined]
        arcade.draw_text(
            TITLE,
            width / 2,
            height - 80,
            TITLE_COLOR,
            TITLE_FONT_SIZE,
            anchor_x="center",
        )

        # Menu
        x = width / 2
        start_y = height - 160
        draw_rows = self.menu.get_draw_model(x, start_y, LINE_HEIGHT)
        for row in draw_rows:
            color = MENU_COLOR if row['enabled'] else MENU_DISABLED_COLOR
            if row['selected']:
                color = MENU_HIGHLIGHT_COLOR
            arcade.draw_text(
                row['text'],
                row['x'],
                row['y'],
                color,
                MENU_FONT_SIZE,
                anchor_x="center" if row['center_x'] else "left",
            )

        # Status message (optional)
        if self._status_message:
            arcade.draw_text(
                self._status_message,
                width / 2,
                80,
                (180, 180, 200),
                14,
                anchor_x="center",
            )
