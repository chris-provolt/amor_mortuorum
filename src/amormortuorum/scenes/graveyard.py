"""The Graveyard hub scene: rest, crypt, and the stairs down."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.hub import GraveyardHub
from ..ui.hud import Hud
from ..ui.menu import MenuItem, MenuView, VerticalMenu

logger = logging.getLogger(__name__)

PANEL_TEXT = (200, 200, 215)


class GraveyardScene(BaseScene):
    """Menu-driven hub. Entering (re)stocks the shop and writes the full save."""

    def __init__(self, app):
        super().__init__(app)
        state = app.state
        self.hub = GraveyardHub(state.save_manager, state.data, meta=state.meta)
        self.menu = VerticalMenu()
        self.mode = "main"
        self._view: MenuView | None = None
        self._title: arcade.Text | None = None
        self._panel: List[arcade.Text] = []
        self.hud: Hud | None = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        run = self.app.state.run
        self.ctx = self.hub.enter()
        run.in_graveyard = True
        self.hub.save_run(run)

        self._title = arcade.Text(
            "The Graveyard", 0, 0, color=arcade.color.GHOST_WHITE, font_size=30,
            anchor_x="center", anchor_y="center",
        )
        self._panel = [
            arcade.Text("", 0, 0, color=PANEL_TEXT, font_size=13, anchor_y="top")
            for _ in range(12)
        ]
        self.hud = Hud(self.app)
        self._view = MenuView(self.menu, 0, 0, font_size=20)
        self._show_main_menu()
        self.on_resize(self.app.width, self.app.height)
        self.hud.push("Saved. The Graveyard is quiet tonight.")
        if self.app.smoke:
            logger.info("Smoke mode: entering the dungeon automatically")
            self._enter_dungeon()

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - 130)
        if self._view is not None:
            self._view.set_position(width * 0.12, height * 0.62)
        for i, line in enumerate(self._panel):
            line.position = (width * 0.52, height * 0.66 - i * 20)
        if self.hud is not None:
            self.hud.on_resize(width, height)

    # Menus

    def _show_main_menu(self) -> None:
        self.mode = "main"
        self.menu.set_items(
            [
                MenuItem(
                    "Enter the Dungeon", self._enter_dungeon, hint="Descend to the next floor"
                ),
                MenuItem("Rest", self._rest, hint="Recover all HP and MP"),
                MenuItem("Crypt", self._show_crypt_menu, hint="Store up to 3 stacks between runs"),
                MenuItem("Return to Title", self._quit_to_title, hint="Your run is saved here"),
            ],
            keep_selection=False,
        )

    def _show_crypt_menu(self) -> None:
        self.mode = "crypt"
        run = self.app.state.run
        data = self.app.state.data
        leader = run.leader
        crypt = self.ctx.crypt
        items: List[MenuItem] = []
        for item_id, qty in sorted(leader.inventory.items.items()):
            item = data.item(item_id)
            can_stack = any(slot.id == item_id for slot in crypt.list_slots())
            items.append(
                MenuItem(
                    f"Deposit  {item.name} x{qty}",
                    lambda iid=item_id: self._deposit(iid),
                    enabled=can_stack or not crypt.is_full(),
                    hint="Crypt is full" if (crypt.is_full() and not can_stack) else "",
                )
            )
        for idx, slot in enumerate(crypt.list_slots()):
            items.append(
                MenuItem(
                    f"Withdraw {slot.name} x{slot.qty}",
                    lambda i=idx: self._withdraw(i),
                )
            )
        items.append(MenuItem("Back", self._show_main_menu))
        self.menu.set_items(items, keep_selection=False)

    # Actions

    def _enter_dungeon(self) -> None:
        from .dungeon import DungeonScene

        run = self.app.state.run
        self.hub.save_run(run)
        run.in_graveyard = False
        logger.info("Leaving the Graveyard for floor B%d", run.floor)
        self.manager.replace(DungeonScene(self.app))

    def _rest(self) -> None:
        self.hub.rest(self.app.state.run.leader)
        self.hud.push("You rest among the stones. HP and MP restored.")

    def _deposit(self, item_id: str) -> None:
        try:
            self.hub.crypt_deposit(self.app.state.run.leader, item_id, 1)
            self.hud.push(f"Stored {self.app.state.data.item(item_id).name} in the Crypt.")
        except AmorError as e:
            self.hud.push(str(e))
        self._show_crypt_menu()

    def _withdraw(self, index: int) -> None:
        try:
            self.hub.crypt_withdraw(self.app.state.run.leader, index, 1)
            self.hud.push("Taken from the Crypt.")
        except AmorError as e:
            self.hud.push(str(e))
        self._show_crypt_menu()

    def _quit_to_title(self) -> None:
        self.hub.save_run(self.app.state.run)
        self.app.state.run = None
        self.manager.pop()

    # Rendering and input

    def _refresh_panel(self) -> None:
        run = self.app.state.run
        data = self.app.state.data
        meta = self.app.state.meta
        p = run.leader
        lines = [
            f"{p.name}   HP {p.hp}/{p.max_hp}   Lv {p.level}   XP {p.xp}",
            f"ATK {p.effective_atk(data)}  DEF {p.effective_df(data)}  SPD {p.effective_spd(data)}",
            f"Next floor: B{run.floor}      Gold: {p.gold}",
            "",
            "Bag:",
        ]
        for item_id, qty in sorted(p.inventory.items.items()):
            lines.append(f"  {data.item(item_id).name} x{qty}")
        lines.append("")
        lines.append(f"Crypt ({len(self.ctx.crypt.list_slots())}/{self.ctx.crypt.capacity}):")
        for slot in self.ctx.crypt.list_slots():
            lines.append(f"  {slot.name} x{slot.qty}")
        lines.append(f"Relics of the Veil: {len(meta.relics.collected)}/10")
        for text, line in zip(self._panel, lines + [""] * len(self._panel)):
            if text.text != line:
                text.text = line

    def draw(self):
        if self._title is not None:
            self._title.draw()
        self._refresh_panel()
        for line in self._panel:
            if line.text:
                line.draw()
        if self._view is not None:
            self._view.draw()
        if self.hud is not None:
            self.hud.draw(self.app.state.run, extra="Graveyard")

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.menu.handle_actions(actions):
            return True
        if "cancel" in actions:
            if self.mode == "crypt":
                self._show_main_menu()
            return True
        return False
