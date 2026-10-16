from __future__ import annotations

import logging

import arcade

from ..core.scenes.base_scene import BaseScene
from ..systems.hub import GraveyardHub
from ..systems.rng import random_seed
from ..systems.run import new_run
from ..systems.stats import bump, check_achievements
from ..ui import pixelart
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui.theme import fs

logger = logging.getLogger(__name__)


class MainMenuScene(BaseScene):
    """Title screen: New Run / Continue / Quit."""

    def __init__(self, app):
        super().__init__(app)
        self._title: arcade.Text | None = None
        self._emblem: arcade.SpriteList | None = None
        self._subtitle: arcade.Text | None = None
        self._footer: arcade.Text | None = None
        self.menu = VerticalMenu()
        self._view: MenuView | None = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        self._title = arcade.Text(
            "Amor Mortuorum", 0, 0, color=arcade.color.GHOST_WHITE, font_size=fs(40),
            anchor_x="center", anchor_y="center",
        )
        self._subtitle = arcade.Text(
            "A descent beneath the Veil", 0, 0, color=arcade.color.GRAY, font_size=fs(16),
            anchor_x="center", anchor_y="center",
        )
        self._footer = arcade.Text(
            "Arrows/WASD move - Enter confirm - Esc back", 0, 0, color=(110, 110, 120),
            font_size=fs(12), anchor_x="center", anchor_y="center",
        )
        self._view = MenuView(self.menu, 0, 0, font_size=fs(22), anchor_x="center")
        self.menu.sfx = self.app.audio.play
        self.app.audio.play_music("graveyard")
        self._rebuild_menu()
        self.on_resize(self.app.width, self.app.height)
        if self.app.smoke and self.app.state.run is None:
            logger.info("Smoke mode: starting a new run automatically")
            self._new_run()

    def on_resume(self):
        super().on_resume()
        self.app.audio.play_music("graveyard")
        self._rebuild_menu()

    def on_resize(self, width: int, height: int):
        self._emblem = arcade.SpriteList()
        self._emblem.append(pixelart.sprite("skull", (width / 2, height * 0.72 + 110), 6))
        if self._title is not None:
            self._title.position = (width / 2, height * 0.72)
        if self._subtitle is not None:
            self._subtitle.position = (width / 2, height * 0.72 - 44)
        if self._footer is not None:
            self._footer.position = (width / 2, 28)
        if self._view is not None:
            self._view.set_position(width / 2, height * 0.46)

    # Menu

    def _hub(self) -> GraveyardHub:
        state = self.app.state
        return GraveyardHub(state.save_manager, state.data, meta=state.meta)

    def _rebuild_menu(self) -> None:
        saved = self._hub().peek_run()
        meta = self.app.state.meta
        if saved is None:
            continue_hint = "No saved run"
        elif saved.in_graveyard:
            continue_hint = f"Resume at the Graveyard, floor B{saved.floor}"
        else:
            continue_hint = f"Resume mid-run at the start of floor B{saved.floor}"
        self.menu.set_items(
            [
                MenuItem("New Run", self._new_run, hint="Begin a fresh descent from the Graveyard"),
                MenuItem("Continue", self._continue, enabled=saved is not None, hint=continue_hint),
                MenuItem(
                    "Relics", self._relics,
                    hint=f"{len(meta.relics.collected)}/10 Relics of the Veil collected",
                ),
                MenuItem("Records", self._records, hint="Lifetime statistics and achievements"),
                MenuItem(
                    f"Profile: {self.app.state.save_manager.profile_id}", self._profiles,
                    hint="Switch or create a save profile",
                ),
                MenuItem("Settings", self._settings, hint="Fullscreen, volumes, bindings"),
                MenuItem(
                    "Quit", self._quit,
                    hint=f"Relics {len(meta.relics.collected)}/10  Deepest B{meta.deepest_floor}",
                ),
            ],
            keep_selection=False,
        )

    def _new_run(self) -> None:
        from .graveyard import GraveyardScene

        state = self.app.state
        seed = state.seed if state.seed is not None else random_seed()
        state.run = new_run(state.data, seed=seed, meta=state.meta)
        bump(state.meta, "runs_started")
        check_achievements(state.meta, state.data)
        state.save_manager.save_meta(state.meta)
        logger.info("New run with seed %d", seed)
        self.manager.push(GraveyardScene(self.app))

    def _continue(self) -> None:
        from .graveyard import GraveyardScene

        run = self._hub().load_run()
        if run is None:
            return
        self.app.state.run = run
        if run.in_graveyard:
            self.manager.push(GraveyardScene(self.app))
        else:
            from .dungeon import DungeonScene

            logger.info("Resuming mid-run on floor B%d", run.floor)
            self.manager.push(DungeonScene(self.app))

    def _records(self) -> None:
        from .records import RecordsScene

        self.manager.push(RecordsScene(self.app))

    def _profiles(self) -> None:
        from .profiles import ProfilesScene

        self.manager.push(ProfilesScene(self.app))

    def _settings(self) -> None:
        from .settings import SettingsScene

        self.manager.push(SettingsScene(self.app))

    def _relics(self) -> None:
        from .relics import RelicsScene

        self.manager.push(RelicsScene(self.app))

    def _quit(self) -> None:
        logger.info("Quit selected from MainMenu")
        self.app.close()

    # Rendering and input

    def draw(self):
        if self._emblem is not None:
            self._emblem.draw(pixelated=True)
        for text in (self._title, self._subtitle, self._footer):
            if text is not None:
                text.draw()
        if self._view is not None:
            self._view.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.menu.handle_actions(actions):
            return True
        if "cancel" in actions:
            self._quit()
            return True
        return False
