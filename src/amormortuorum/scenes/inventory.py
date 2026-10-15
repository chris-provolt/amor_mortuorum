"""Bag and equipment screen, reachable from the Graveyard and the dungeon (Tab)."""
from __future__ import annotations

import logging
from typing import List

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.entities import EQUIP_SLOTS
from ..systems.progression import xp_to_next_level
from ..ui.menu import MenuItem, MenuView, VerticalMenu

logger = logging.getLogger(__name__)

PANEL_TEXT = (200, 200, 215)
MSG = (255, 215, 120)


class InventoryScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.run = app.state.run
        self.data = app.state.data
        self.member = 0  # index into run.party; Left/Right cycles
        self.menu = VerticalMenu()
        self._view: MenuView | None = None
        self._title: arcade.Text | None = None
        self._panel: List[arcade.Text] = []
        self._msg: arcade.Text | None = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        self._title = arcade.Text(
            "Bag & Equipment", 0, 0, color=arcade.color.GHOST_WHITE, font_size=28,
            anchor_x="center", anchor_y="center",
        )
        self._panel = [
            arcade.Text("", 0, 0, color=PANEL_TEXT, font_size=14, anchor_y="top") for _ in range(8)
        ]
        self._msg = arcade.Text("", 0, 0, color=MSG, font_size=14, anchor_x="center")
        self._view = MenuView(self.menu, 0, 0, font_size=17)
        self._build_menu()
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._title is not None:
            self._title.position = (width / 2, height - 50)
        if self._view is not None:
            self._view.set_position(width * 0.08, height * 0.78)
        for i, line in enumerate(self._panel):
            line.position = (width * 0.58, height * 0.80 - i * 24)
        if self._msg is not None:
            self._msg.position = (width / 2, 40)

    # Menu

    @property
    def player(self):
        return self.run.party[self.member]

    @property
    def bag(self):
        return self.run.leader.inventory

    def _build_menu(self) -> None:
        p = self.player
        items: List[MenuItem] = []
        for slot in EQUIP_SLOTS:
            item_id = p.equipment.slots.get(slot)
            name = self.data.item(item_id).name if item_id else "-"
            items.append(
                MenuItem(
                    f"{slot.title():<10} {name}",
                    (lambda s=slot: self._unequip(s)) if item_id else None,
                    enabled=item_id is not None,
                    hint="Enter: unequip to bag" if item_id else "",
                )
            )
        items.append(MenuItem("Bag (shared)", enabled=False))
        for item_id, qty in sorted(self.bag.items.items()):
            item = self.data.item(item_id)
            if item.slot is not None:
                stat = f"ATK+{item.atk}" if item.atk else f"DEF+{item.df}" if item.df else (
                    f"SPD+{item.spd}" if item.spd else ""
                )
                items.append(
                    MenuItem(
                        f"  {item.name} x{qty}",
                        lambda iid=item_id: self._equip(iid),
                        hint=f"Enter: equip ({item.type}, {stat})",
                    )
                )
            elif item.is_consumable and (item.hp_restore > 0 or item.mp_restore > 0):
                effect = (
                    f"heals {item.hp_restore}" if item.hp_restore
                    else f"restores {item.mp_restore} MP"
                )
                items.append(
                    MenuItem(
                        f"  {item.name} x{qty}",
                        lambda iid=item_id: self._use(iid),
                        hint=f"Enter: use ({effect})",
                    )
                )
            else:
                hint = "Revives you at the Graveyard on death" if item.revive else "Combat only"
                items.append(MenuItem(f"  {item.name} x{qty}", None, hint=hint))
        items.append(MenuItem("Back", self._back))
        self.menu.set_items(items)

    def _say(self, text: str) -> None:
        if self._msg is not None:
            self._msg.text = text

    def _equip(self, item_id: str) -> None:
        item = self.data.item(item_id)
        try:
            previous = self.player.equip_from(self.bag, item, self.data)
        except AmorError as e:
            self._say(str(e))
            return
        swap = f" (swapped out {self.data.item(previous).name})" if previous else ""
        self._say(f"{self.player.name} equips {item.name}{swap}.")
        self._build_menu()

    def _unequip(self, slot: str) -> None:
        try:
            item_id = self.player.unequip_to(self.bag, slot, self.data)
        except AmorError as e:
            self._say(str(e))
            return
        if item_id:
            self._say(f"Unequipped {self.data.item(item_id).name}.")
        self._build_menu()

    def _use(self, item_id: str) -> None:
        item = self.data.item(item_id)
        p = self.player
        if not p.is_alive:
            self._say(f"{p.name} is down; only rest at the Graveyard helps now.")
            return
        if item.hp_restore and not item.mp_restore and p.hp >= p.max_hp:
            self._say("You are already at full health.")
            return
        if item.mp_restore and not item.hp_restore and p.stats.mp >= p.stats.max_mp:
            self._say("Your mind is already clear.")
            return
        mp_before = p.stats.mp
        try:
            healed = p.use_consumable_from(self.bag, item)
        except AmorError as e:
            self._say(str(e))
            return
        gained_mp = p.stats.mp - mp_before
        effect = f"recovered {healed} HP" if item.hp_restore else f"regained {gained_mp} MP"
        self._say(f"{p.name} uses {item.name}: {effect}.")
        self._build_menu()

    def _back(self) -> None:
        self.manager.pop()

    # Rendering and input

    def _refresh_panel(self) -> None:
        p = self.player
        d = self.data
        nxt = xp_to_next_level(p, d)
        who = f"{p.name}   Level {p.level}"
        if len(self.run.party) > 1:
            who += f"   ({self.member + 1}/{len(self.run.party)}, Left/Right to switch)"
        lines = [
            who,
            f"XP {p.xp}" + (f"   next in {nxt}" if nxt is not None else "   (max)"),
            f"HP {p.hp}/{p.max_hp}   MP {p.stats.mp}/{p.stats.max_mp}",
            f"ATK {p.effective_atk(d)}  (base {p.stats.atk})",
            f"DEF {p.effective_df(d)}  (base {p.stats.df})",
            f"SPD {p.effective_spd(d)}  (base {p.stats.spd})",
            f"Gold {p.gold}",
            f"Floor B{self.run.floor}",
        ]
        for text, line in zip(self._panel, lines):
            if text.text != line:
                text.text = line

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 200))
        if self._title is not None:
            self._title.draw()
        self._refresh_panel()
        for line in self._panel:
            line.draw()
        if self._view is not None:
            self._view.draw()
        if self._msg is not None and self._msg.text:
            self._msg.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.menu.handle_actions(actions):
            return True
        if "move_left" in actions or "move_right" in actions:
            step = 1 if "move_right" in actions else -1
            self.member = (self.member + step) % len(self.run.party)
            self._say("")
            self._build_menu()
            return True
        if "cancel" in actions or "menu" in actions:
            self._back()
            return True
        return False
