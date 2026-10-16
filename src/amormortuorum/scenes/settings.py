"""Settings screen: fullscreen, volumes, and a read-only view of key bindings."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..core.settings import user_settings_path
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui.theme import MAX_SCALE, MIN_SCALE, set_ui_scale, ui_scale
from ..ui.theme import fs

logger = logging.getLogger(__name__)

TEXT = (215, 215, 230)
DIM = (120, 120, 135)
STEP = 0.1


class SettingsScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.settings = app.settings
        self.menu = VerticalMenu()
        self._view: MenuView | None = None
        self._title: arcade.Text | None = None
        self._bindings: List[arcade.Text] = []
        self._msg: arcade.Text | None = None
        self.mode = "main"  # main | keys | listen
        self._listen_action: str | None = None

    def on_enter(self):
        super().on_enter()
        self._title = arcade.Text(
            "Settings", 0, 0, color=arcade.color.GHOST_WHITE, font_size=fs(28),
            anchor_x="center", anchor_y="center",
        )
        self._msg = arcade.Text(
            "", 0, 0, color=(255, 215, 120), font_size=fs(13), anchor_x="center"
        )
        self._view = MenuView(self.menu, 0, 0, font_size=fs(18))
        self.menu.sfx = self.app.audio.play
        self._refresh_bindings()
        self._build_menu()
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - 50)
        if self._view is not None:
            self._view.set_position(width * 0.08, height * 0.74)
        for i, line in enumerate(self._bindings):
            line.position = (width * 0.56, height * 0.78 - i * 19)
        if self._msg is not None:
            self._msg.position = (width / 2, 36)

    # Menu

    def _pct(self, value: float) -> str:
        return f"{int(round(value * 100)):>3}%"

    def _refresh_bindings(self) -> None:
        mapping = self.app.input.mapping_names()
        self._bindings = [
            arcade.Text("Key bindings", 0, 0, color=TEXT, font_size=fs(14), anchor_y="top")
        ] + [
            arcade.Text(f"{action:<12} {', '.join(keys)}", 0, 0, color=DIM, font_size=fs(12),
                        anchor_y="top")
            for action, keys in mapping.items()
        ]
        self.on_resize(self.app.width, self.app.height)

    def _build_keys_menu(self) -> None:
        self.mode = "keys"
        mapping = self.app.input.mapping_names()
        items = [
            MenuItem(
                f"{action:<12} {', '.join(keys)}",
                lambda a=action: self._listen_for(a),
                hint="Enter, then press the new key (Esc cancels)",
            )
            for action, keys in mapping.items()
        ]
        items.append(MenuItem("Back", self._build_menu))
        self.menu.set_items(items, keep_selection=False)

    def _listen_for(self, action: str) -> None:
        self.mode = "listen"
        self._listen_action = action
        self._say(f"Press a key for '{action}'...")

    def _apply_rebind(self, code: int) -> None:
        action = self._listen_action or ""
        name = self.app.input.rebind_key(action, code)
        mapping = {a: list(k) for a, k in self.settings.input.mapping.items()}
        for other in mapping:
            if other != action and name in mapping[other]:
                mapping[other] = [k for k in mapping[other] if k != name]
        mapping[action] = [name]
        self.settings.input.mapping = mapping
        self._listen_action = None
        self._say(f"'{action}' is now {name}. Save to keep it.")
        self._refresh_bindings()
        self._build_keys_menu()

    def _build_menu(self) -> None:
        self.mode = "main"
        s = self.settings
        pad = self.app.controller.connected if self.app.controller else None
        self.menu.set_items(
            [
                MenuItem(
                    f"Fullscreen      {'On' if self.app.fullscreen else 'Off'}",
                    self._toggle_fullscreen, hint="Enter toggles",
                ),
                MenuItem(
                    f"Music volume   {self._pct(s.audio.music_volume)}", None,
                    hint="Left / Right adjust", payload="music",
                ),
                MenuItem(
                    f"SFX volume     {self._pct(s.audio.sfx_volume)}", None,
                    hint="Left / Right adjust", payload="sfx",
                ),
                MenuItem(
                    f"VSync           {'On' if s.video.vsync else 'Off'}", self._toggle_vsync,
                    hint="Enter toggles (applies next launch)",
                ),
                MenuItem(
                    f"UI scale        {int(round(ui_scale() * 100)):>3}%", None,
                    hint="Left / Right adjust; applies when a screen is reopened",
                    payload="scale",
                ),
                MenuItem("Rebind keys", self._build_keys_menu, hint="Change one key per action"),
                MenuItem(
                    f"Controller      {pad or 'none detected'}", None,
                    hint="Xbox-style: A confirm, B back, Y bag, X map, Start pause",
                ),
                MenuItem("Save", self._save, hint=f"Writes {user_settings_path()}"),
                MenuItem("Back", self._back),
            ]
        )

    def _say(self, text: str) -> None:
        if self._msg is not None:
            self._msg.text = text

    def _toggle_fullscreen(self) -> None:
        self.app.toggle_fullscreen()
        self.settings.video.fullscreen = bool(self.app.fullscreen)
        self._build_menu()

    def _toggle_vsync(self) -> None:
        self.settings.video.vsync = not self.settings.video.vsync
        try:
            self.app.set_vsync(self.settings.video.vsync)
        except Exception:  # pragma: no cover - driver specific
            pass
        self._build_menu()

    def _adjust(self, payload: str, delta: float) -> None:
        audio = self.settings.audio
        if payload == "music":
            audio.music_volume = round(max(0.0, min(1.0, audio.music_volume + delta)), 2)
        elif payload == "sfx":
            audio.sfx_volume = round(max(0.0, min(1.0, audio.sfx_volume + delta)), 2)
            self.app.audio.play("menu_move")
        elif payload == "scale":
            value = round(max(MIN_SCALE, min(MAX_SCALE, ui_scale() + delta)), 2)
            self.settings.video.ui_scale = set_ui_scale(value)
        self.app.audio.apply_volumes()
        selected = self.menu.selected
        self._build_menu()
        self.menu.selected = selected

    def _save(self) -> None:
        path = user_settings_path()
        self.settings.save(path)
        self._say(f"Saved to {path}")

    def _back(self) -> None:
        self.manager.pop()

    # Rendering and input

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 210))
        if self._title is not None:
            self._title.draw()
        if self._view is not None:
            self._view.draw()
        for line in self._bindings:
            line.draw()
        if self._msg is not None and self._msg.text:
            self._msg.draw()

    def on_key_press(self, key: int, modifiers: int):
        if self.mode == "listen" and self._listen_action is not None:
            self._apply_rebind(key)

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.mode == "listen":
            if "cancel" in actions:
                self._listen_action = None
                self._say("Rebind cancelled.")
                self._build_keys_menu()
                return True
            return False  # let the raw key reach on_key_press
        current = self.menu.current
        if current is not None and current.payload in ("music", "sfx", "scale"):
            if "move_left" in actions:
                self._adjust(current.payload, -STEP)
                return True
            if "move_right" in actions:
                self._adjust(current.payload, +STEP)
                return True
        if self.menu.handle_actions(actions):
            return True
        if "cancel" in actions:
            if self.mode == "keys":
                self._build_menu()
            else:
                self._back()
            return True
        return False
