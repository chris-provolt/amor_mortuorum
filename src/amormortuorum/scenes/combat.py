"""Turn-based combat scene: command menu, target cycling, log, HP panels."""
from __future__ import annotations

import logging
from collections import deque
from typing import Deque, List, Optional

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.combat import Action, ActionKind, Battle, LogEvent, Outcome
from ..ui.menu import MenuItem, MenuView, VerticalMenu

logger = logging.getLogger(__name__)

TEXT = (230, 230, 240)
DIM = (150, 150, 165)
HP_BACK = (60, 30, 30)
HP_FRONT = (190, 60, 60)
HP_PARTY = (70, 170, 110)
TARGET = (255, 215, 120)
PANEL = (0, 0, 0, 150)
LOG_COLORS = {
    "attack": (230, 200, 200),
    "heal": (170, 230, 180),
    "item": (200, 220, 240),
    "defend": (200, 200, 230),
    "flee": (230, 220, 160),
    "defeat": (240, 130, 130),
    "victory": (255, 215, 120),
    "info": DIM,
}


class CombatScene(BaseScene):
    def __init__(self, app, battle: Battle):
        super().__init__(app)
        self.battle = battle
        self.data = app.state.data
        self.mode = "command"  # command | item | done
        self.actor = 0
        self.target: Optional[int] = battle.first_living_enemy_index()
        self.menu = VerticalMenu()
        self._view: Optional[MenuView] = None
        self._log: Deque[LogEvent] = deque(maxlen=7)
        self._log_rows: List[arcade.Text] = []
        self._enemy_rows: List[arcade.Text] = []
        self._party_rows: List[arcade.Text] = []
        self._header: Optional[arcade.Text] = None
        self._prompt: Optional[arcade.Text] = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        names = ", ".join(e.name for e in self.battle.enemies)
        self._header = arcade.Text(
            f"Ambush! {names}", 0, 0, color=TEXT, font_size=20, anchor_x="center", anchor_y="top"
        )
        self._prompt = arcade.Text("", 0, 0, color=DIM, font_size=12, anchor_x="center")
        self._log_rows = [arcade.Text("", 0, 0, font_size=13, anchor_y="top") for _ in range(7)]
        self._enemy_rows = [
            arcade.Text("", 0, 0, color=TEXT, font_size=15, anchor_y="center")
            for _ in self.battle.enemies
        ]
        self._party_rows = [
            arcade.Text("", 0, 0, color=TEXT, font_size=15, anchor_y="center")
            for _ in self.battle.party
        ]
        self._view = MenuView(self.menu, 0, 0, font_size=20)
        self._log.append(LogEvent("The dead stir.", "info"))
        self._pick_next_actor()
        self._show_command_menu()
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self._header is not None:
            self._header.position = (width / 2, height - 18)
        if self._prompt is not None:
            self._prompt.position = (width / 2, 22)
        for i, row in enumerate(self._enemy_rows):
            row.position = (width * 0.08, height * 0.74 - i * 46)
        for i, row in enumerate(self._party_rows):
            row.position = (width * 0.08, height * 0.26 - i * 46)
        for i, row in enumerate(self._log_rows):
            row.position = (width * 0.52, height * 0.78 - i * 20)
        if self._view is not None:
            self._view.set_position(width * 0.56, height * 0.30)

    # Menus

    def _show_command_menu(self) -> None:
        self.mode = "command"
        self.menu.set_items(
            [
                MenuItem("Attack", self._attack, hint="Left/Right to change target"),
                MenuItem("Item", self._show_item_menu, hint="Use a potion or scroll"),
                MenuItem("Defend", self._defend, hint="Halve damage this round"),
                MenuItem("Flee", self._flee, hint="Chance depends on speed"),
            ],
            keep_selection=False,
        )

    def _show_item_menu(self) -> None:
        player = self.battle.party[self.actor]
        items: List[MenuItem] = []
        for item_id, qty in sorted(player.inventory.items.items()):
            item = self.data.item(item_id)
            if not item.usable_in_combat:
                continue
            effect = f"Heals {item.hp_restore}" if item.hp_restore else f"Deals {item.damage}"
            items.append(
                MenuItem(
                    f"{item.name} x{qty}", lambda iid=item_id: self._use_item(iid), hint=effect
                )
            )
        if not items:
            self._log.append(LogEvent("Nothing in the bag can help here.", "info"))
            return
        items.append(MenuItem("Back", self._show_command_menu))
        self.mode = "item"
        self.menu.set_items(items, keep_selection=False)

    # Actions

    def _pick_next_actor(self) -> None:
        for b in self.battle.living_players:
            if b.index not in self.battle.pending:
                self.actor = b.index
                return

    def _submit(self, action: Action) -> None:
        try:
            events = self.battle.submit(action)
        except AmorError as e:
            self._log.append(LogEvent(str(e), "info"))
            return
        self._log.extend(events)
        if self.battle.outcome is not Outcome.ONGOING:
            self.mode = "done"
            self.menu.set_items([], keep_selection=False)
            return
        self._pick_next_actor()
        self._refresh_target()
        self._show_command_menu()

    def _attack(self) -> None:
        self._refresh_target()
        self._submit(Action(ActionKind.ATTACK, self.actor, target=self.target))

    def _defend(self) -> None:
        self._submit(Action(ActionKind.DEFEND, self.actor))

    def _flee(self) -> None:
        self._submit(Action(ActionKind.FLEE, self.actor))

    def _use_item(self, item_id: str) -> None:
        item = self.data.item(item_id)
        target = self.target if item.damage > 0 else self.actor
        self._submit(Action(ActionKind.ITEM, self.actor, target=target, item_id=item_id))

    def _refresh_target(self) -> None:
        living = [b.index for b in self.battle.living_enemies]
        if not living:
            self.target = None
        elif self.target not in living:
            self.target = living[0]

    def _cycle_target(self, step: int) -> None:
        living = [b.index for b in self.battle.living_enemies]
        if not living:
            return
        if self.target not in living:
            self.target = living[0]
            return
        self.target = living[(living.index(self.target) + step) % len(living)]

    def _finish(self) -> None:
        if self.battle.outcome is Outcome.VICTORY:
            self.battle.apply_rewards()
        self.manager.pop()

    # Rendering

    def _draw_bar(self, x: float, y: float, frac: float, color, width: float = 180) -> None:
        arcade.draw_lbwh_rectangle_filled(x, y, width, 8, HP_BACK)
        arcade.draw_lbwh_rectangle_filled(x, y, width * max(0.0, min(1.0, frac)), 8, color)

    def draw(self):
        w, h = self.app.width, self.app.height
        arcade.draw_lbwh_rectangle_filled(0, 0, w, h, PANEL)
        if self._header is not None:
            self._header.draw()

        for row, b in zip(self._enemy_rows, self.battle.foes):
            marker = ">" if (b.index == self.target and b.is_alive) else " "
            text = f"{marker} {b.name}   {max(0, b.stats.hp)}/{b.stats.max_hp}"
            if row.text != text:
                row.text = text
            row.color = DIM if not b.is_alive else TARGET if b.index == self.target else TEXT
            row.draw()
            self._draw_bar(row.x + 12, row.y - 20, b.stats.hp / b.stats.max_hp, HP_FRONT)

        for row, b in zip(self._party_rows, self.battle.players):
            marker = ">" if (b.index == self.actor and self.mode != "done") else " "
            text = f"{marker} {b.name}   HP {max(0, b.stats.hp)}/{b.stats.max_hp}"
            if b.defending:
                text += "  [guard]"
            if row.text != text:
                row.text = text
            row.color = DIM if not b.is_alive else TEXT
            row.draw()
            self._draw_bar(row.x + 12, row.y - 20, b.stats.hp / b.stats.max_hp, HP_PARTY)

        for row, event in zip(self._log_rows, list(self._log)[::-1]):
            if row.text != event.text:
                row.text = event.text
            row.color = LOG_COLORS.get(event.kind, DIM)
            row.draw()

        if self.mode == "done":
            prompt = {
                Outcome.VICTORY: "Victory. Press Enter to continue.",
                Outcome.DEFEAT: "The party has fallen. Press Enter.",
                Outcome.FLED: "Escaped. Press Enter to continue.",
            }.get(self.battle.outcome, "")
        else:
            prompt = f"Round {self.battle.round_number}: choose an action"
        if self._prompt.text != prompt:
            self._prompt.text = prompt
        self._prompt.draw()
        if self._view is not None and self.mode != "done":
            self._view.draw()

    # Input

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.mode == "done":
            if "confirm" in actions:
                self._finish()
            return True
        if "move_left" in actions:
            self._cycle_target(-1)
            return True
        if "move_right" in actions:
            self._cycle_target(+1)
            return True
        if self.menu.handle_actions(actions):
            return True
        if "cancel" in actions:
            if self.mode == "item":
                self._show_command_menu()
            return True
        return False
