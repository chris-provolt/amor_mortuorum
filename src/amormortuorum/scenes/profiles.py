"""Profile picker: switch between save profiles or create a new one."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..core.settings import user_settings_path
from ..persistence import SaveManager
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui.theme import fs

logger = logging.getLogger(__name__)

TEXT = (215, 215, 230)
MAX_PROFILES = 8


def next_profile_name(existing: List[str]) -> str:
    n = 2
    while f"profile{n}" in existing:
        n += 1
    return f"profile{n}"


class ProfilesScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.menu = VerticalMenu()
        self._view: MenuView | None = None
        self._title: arcade.Text | None = None
        self._msg: arcade.Text | None = None

    def on_enter(self):
        super().on_enter()
        self._title = arcade.Text(
            "Profiles", 0, 0, color=arcade.color.GHOST_WHITE, font_size=fs(28),
            anchor_x="center", anchor_y="center",
        )
        self._msg = arcade.Text(
            "", 0, 0, color=(255, 215, 120), font_size=fs(13), anchor_x="center"
        )
        self._view = MenuView(self.menu, 0, 0, font_size=fs(20), anchor_x="center")
        self.menu.sfx = self.app.audio.play
        self._build_menu()
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - fs(60))
        if self._view is not None:
            self._view.set_position(width / 2, height * 0.66)
        if self._msg is not None:
            self._msg.position = (width / 2, fs(40))

    def _profiles(self) -> List[str]:
        current = self.app.state.save_manager.profile_id
        names = SaveManager.list_profiles(self.app.state.save_manager.root_dir)
        if current not in names:
            names.append(current)
        return sorted(names)

    def _build_menu(self) -> None:
        current = self.app.state.save_manager.profile_id
        names = self._profiles()
        items = [
            MenuItem(
                f"{name}{'   (active)' if name == current else ''}",
                lambda n=name: self._select(n),
                hint="Enter to switch" if name != current else "This profile is in use",
            )
            for name in names
        ]
        items.append(
            MenuItem(
                "New profile", self._create, enabled=len(names) < MAX_PROFILES,
                hint="Starts with an empty Crypt and no relics",
            )
        )
        items.append(MenuItem("Back", self._back))
        self.menu.set_items(items, keep_selection=False)

    def _say(self, text: str) -> None:
        if self._msg is not None:
            self._msg.text = text

    def _select(self, name: str) -> None:
        if name == self.app.state.save_manager.profile_id:
            self._back()
            return
        self.app.switch_profile(name)
        try:
            self.app.settings.save(user_settings_path())
        except OSError as e:  # pragma: no cover - disk specific
            logger.warning("Could not persist profile choice: %s", e)
        self._say(f"Now playing as {name}.")
        self._build_menu()

    def _create(self) -> None:
        name = next_profile_name(self._profiles())
        self._select(name)

    def _back(self) -> None:
        self.manager.pop()

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 210))
        if self._title is not None:
            self._title.draw()
        if self._view is not None:
            self._view.draw()
        if self._msg is not None and self._msg.text:
            self._msg.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.menu.handle_actions(actions):
            return True
        if "cancel" in actions:
            self._back()
            return True
        return False
