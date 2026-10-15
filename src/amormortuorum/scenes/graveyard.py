"""The Graveyard hub scene: rest, crypt, and the stairs down."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.hub import GraveyardHub
from ..systems.party import MAX_PARTY, available_companions, recruit
from ..systems.progression import xp_to_next_level
from ..systems.relics import apply_passives
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
        apply_passives(run, self.app.state.meta, self.app.state.data)
        self.hub.save_run(run)

        self._title = arcade.Text(
            "The Graveyard", 0, 0, color=arcade.color.GHOST_WHITE, font_size=30,
            anchor_x="center", anchor_y="center",
        )
        self._panel = [
            arcade.Text("", 0, 0, color=PANEL_TEXT, font_size=13, anchor_y="top")
            for _ in range(16)
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
                MenuItem("Shop", self._show_shop_menu, hint="Limited stock; restocks each visit"),
                MenuItem("Crypt", self._show_crypt_menu, hint="Store up to 3 stacks between runs"),
                MenuItem("Recruit", self._show_recruit_menu, hint="Hire companions (up to 4)"),
                MenuItem("Bag & Equipment", self._open_inventory, hint="Equip gear, use potions"),
                MenuItem(
                    "Relics of the Veil", self._open_relics, hint="Your collection and passives"
                ),
                MenuItem("Return to Title", self._quit_to_title, hint="Your run is saved here"),
            ],
            keep_selection=False,
        )

    def _show_shop_menu(self) -> None:
        self.mode = "shop"
        leader = self.app.state.run.leader
        data = self.app.state.data
        items: List[MenuItem] = []
        for item_id, entry in sorted(self.ctx.shop.stock().items()):
            item = data.item(item_id)
            effect = (
                f"Heals {item.hp_restore}" if item.hp_restore
                else f"Deals {item.damage} in combat" if item.damage
                else item.type
            )
            items.append(
                MenuItem(
                    f"{item.name:<24} {entry.price:>4}g   x{entry.quantity}",
                    lambda iid=item_id: self._buy(iid),
                    enabled=leader.gold >= entry.price,
                    hint=effect if leader.gold >= entry.price else f"Not enough gold ({effect})",
                )
            )
        if not items:
            items.append(MenuItem("Sold out", None, enabled=False))
        items.append(MenuItem("Back", self._show_main_menu))
        self.menu.set_items(items, keep_selection=False)

    def _show_recruit_menu(self) -> None:
        self.mode = "recruit"
        run = self.app.state.run
        data = self.app.state.data
        items: List[MenuItem] = []
        full = len(run.party) >= MAX_PARTY
        for comp in available_companions(run, data):
            st = comp.stats
            stats = (
                f"HP {st['max_hp']} MP {st['max_mp']} ATK {st['atk']} "
                f"DEF {st['df']} SPD {st['spd']}"
            )
            can = not full and run.leader.gold >= comp.cost
            hint = comp.desc + f"  [{stats}]"
            if full:
                hint = "The party is full"
            elif run.leader.gold < comp.cost:
                hint = f"Not enough gold ({comp.cost})  {stats}"
            items.append(
                MenuItem(
                    f"{comp.name:<16} {comp.cost:>4}g", lambda cid=comp.id: self._recruit(cid),
                    enabled=can, hint=hint,
                )
            )
        if not items:
            items.append(MenuItem("No one else waits by the gate", None, enabled=False))
        items.append(MenuItem("Back", self._show_main_menu))
        self.menu.set_items(items, keep_selection=False)

    def _recruit(self, companion_id: str) -> None:
        try:
            member = recruit(self.app.state.run, companion_id, self.app.state.data)
            self.hud.push(f"{member.name} joins you.")
            self.hub.save_run(self.app.state.run)
        except AmorError as e:
            self.hud.push(str(e))
        self._show_recruit_menu()

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
        self.hub.rest_party(self.app.state.run)
        self.hud.push("You rest among the stones. HP and MP restored.")

    def _buy(self, item_id: str) -> None:
        leader = self.app.state.run.leader
        try:
            spent = self.ctx.shop.buy(leader, item_id, 1)
            self.hud.push(f"Bought {self.app.state.data.item(item_id).name} for {spent} gold.")
        except AmorError as e:
            self.hud.push(str(e))
        selected = self.menu.selected
        self._show_shop_menu()
        self.menu.selected = min(selected, len(self.menu) - 1)
        self.menu.move(0)

    def _open_inventory(self) -> None:
        from .inventory import InventoryScene

        self.manager.push(InventoryScene(self.app))

    def _open_relics(self) -> None:
        from .relics import RelicsScene

        self.manager.push(RelicsScene(self.app))

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
        nxt = xp_to_next_level(p, data)
        xp_text = f"XP {p.xp}" + (f" (next in {nxt})" if nxt is not None else " (max)")
        lines = [
            f"{p.name}   HP {p.hp}/{p.max_hp}   Lv {p.level}   {xp_text}",
            f"ATK {p.effective_atk(data)}  DEF {p.effective_df(data)}  SPD {p.effective_spd(data)}",
            f"Next floor: B{run.floor}      Gold: {p.gold}",
        ]
        for m in run.party[1:]:
            lines.append(f"  {m.name}   HP {m.hp}/{m.max_hp}   Lv {m.level}")
        lines += ["", "Bag:"]
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
            if self.mode != "main":
                self._show_main_menu()
            return True
        if "menu" in actions:
            self._open_inventory()
            return True
        return False
