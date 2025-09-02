from __future__ import annotations

import logging
from typing import Optional

from ...save_system import SaveManager
from ...settings import SettingsManager

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover
    arcade = None  # type: ignore

from ..widgets import Button

log = logging.getLogger(__name__)


class MainMenuView(arcade.View):  # pragma: no cover - UI rendering
    """Main menu with New / Continue / Settings / Quit.

    Continue is disabled if no snapshot exists.
    """

    def __init__(self, settings: SettingsManager, saves: SaveManager):
        super().__init__()
        self.settings_mgr = settings
        self.save_mgr = saves
        self.buttons: list[Button] = []
        self._continue_btn: Optional[Button] = None

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)
        self.settings_mgr.adapter.bind_window(self.window)
        self.settings_mgr.apply()
        self._build_ui()

    def _build_ui(self) -> None:
        # Centering base position
        cx = self.window.width / 2
        cy = self.window.height / 2
        gap = 60

        def new_game():
            log.info("Starting New Game")
            try:
                self.save_mgr.delete_snapshot()
            except Exception:
                pass
            # Placeholder: swap to actual Game view
            arcade.draw_text("New Game starting...", 10, 10, arcade.color.WHITE, 14)

        def continue_game():
            log.info("Continue selected")
            # Placeholder: load snapshot and swap to Game view
            try:
                snap = self.save_mgr.load_snapshot()
                log.info("Loaded snapshot: %s", snap)
            except Exception as e:
                log.warning("Continue failed: %s", e)

        def open_settings():
            from .settings_view import SettingsView
            self.window.show_view(SettingsView(self.settings_mgr, self.save_mgr))

        def quit_game():
            arcade.close_window()

        self.buttons = [
            Button(cx, cy + gap, 240, 44, "New", new_game),
            Button(cx, cy, 240, 44, "Continue", continue_game, disabled=not self.save_mgr.has_snapshot()),
            Button(cx, cy - gap, 240, 44, "Settings", open_settings),
            Button(cx, cy - 2 * gap, 240, 44, "Quit", quit_game),
        ]
        self._continue_btn = self.buttons[1]

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text(
            "Amor Mortuorum",
            self.window.width / 2,
            self.window.height - 120,
            arcade.color.ALMOND,
            36,
            anchor_x="center",
        )
        for b in self.buttons:
            b.draw()
        # Update continue disabled state dynamically (in case snapshot was created/deleted)
        if self._continue_btn is not None:
            self._continue_btn.disabled = not self.save_mgr.has_snapshot()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        for b in self.buttons:
            if b.hit_test(x, y):
                b.click()
                break

    def on_key_press(self, key: int, modifiers: int):
        if key in (arcade.key.ENTER, arcade.key.RETURN):
            # Activate first enabled button (New or Continue)
            for b in self.buttons:
                if not b.disabled:
                    b.click()
                    break
        elif key == arcade.key.ESCAPE:
            arcade.close_window()
