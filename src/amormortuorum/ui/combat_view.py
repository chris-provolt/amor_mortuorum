from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import arcade

from amormortuorum.combat.actions import Action, Command
from amormortuorum.combat.command_menu import CommandMenu, MenuState, Target

logger = logging.getLogger(__name__)

# Basic window dimensions for the combat scene
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
TITLE = "Amor Mortuorum - Combat"

# Colors
COLOR_BG = arcade.color.BLACK
COLOR_PANEL = arcade.color.DARK_SLATE_GRAY
COLOR_TEXT = arcade.color.WHITE
COLOR_HILITE = arcade.color.AMBER
COLOR_CURSOR = arcade.color.YELLOW
COLOR_ENEMY = arcade.color.LIGHT_CORAL
COLOR_ENEMY_DEAD = arcade.color.DARK_RED


@dataclass
class Enemy:
    """Minimal enemy representation for UI placement.

    In a full implementation, this would reference the game's combatant models.
    """

    id: str
    name: str
    x: float
    y: float
    alive: bool = True


class CombatView(arcade.View):
    """Arcade View implementing a combat UI skeleton with command menu and target selection.

    Keyboard controls:
    - Up/Down: navigate menu
    - Enter/Space: confirm selection (menu or target)
    - Esc/Backspace: cancel target selection
    - Left/Right (in target selection): move target cursor
    """

    def __init__(self):
        super().__init__()
        self.menu = CommandMenu()
        # Placeholder list of enemies for target selection demonstration
        self.enemies: List[Enemy] = [
            Enemy(id="e1", name="Ghoul", x=650, y=380),
            Enemy(id="e2", name="Wraith", x=780, y=320),
            Enemy(id="e3", name="Bonepile", x=710, y=240),
        ]
        # Action log to show the effect of selection; in real combat this would queue actions.
        self._action_log: List[Action] = []
        self._message: str = ""

    # --- View lifecycle ---

    def on_show_view(self):
        arcade.set_background_color(COLOR_BG)
        self._message = "Select a command"
        logger.debug("CombatView shown. Initialized message and menu.")

    # --- Rendering ---

    def on_draw(self):
        arcade.start_render()

        # Draw enemy placeholders
        for idx, enemy in enumerate(self.enemies):
            color = COLOR_ENEMY if enemy.alive else COLOR_ENEMY_DEAD
            arcade.draw_rectangle_filled(enemy.x, enemy.y, 120, 60, color)
            arcade.draw_text(
                enemy.name,
                enemy.x - 50,
                enemy.y - 8,
                COLOR_TEXT,
                14,
                bold=True,
            )

        # Draw target cursor if in target selection
        if self.menu.state == MenuState.TARGET_SELECT:
            # Map the menu's target index to the on-screen enemy
            selectable = [e for e in self.enemies if e.alive]
            if selectable:
                # The menu stores only alive targets in order it was passed
                target = selectable[self.menu.target_index]
                self._draw_target_cursor(target.x, target.y + 50)

        # Draw command panel
        self._draw_command_panel()

        # Draw message/action log line
        if self._message:
            arcade.draw_text(self._message, 20, 500, COLOR_TEXT, 14)

    def _draw_command_panel(self):
        # Panel box
        panel_x = 20
        panel_y = 20
        panel_w = 360
        panel_h = 220
        arcade.draw_lrtb_rectangle_filled(panel_x, panel_x + panel_w, panel_y + panel_h, panel_y, COLOR_PANEL)

        # Title
        arcade.draw_text("Commands", panel_x + 14, panel_y + panel_h - 28, COLOR_TEXT, 16, bold=True)

        # Commands list
        base_y = panel_y + panel_h - 60
        for i, cmd in enumerate(self.menu.options):
            y = base_y - i * 32
            # Highlight selected option in menu state
            color = COLOR_HILITE if (self.menu.state == MenuState.MENU and i == self.menu.index) else COLOR_TEXT
            arcade.draw_text(cmd.value, panel_x + 50, y, color, 16)

        # Draw menu cursor arrow if in MENU
        if self.menu.state == MenuState.MENU:
            y = base_y - self.menu.index * 32
            arcade.draw_text(">",  panel_x + 24, y, COLOR_CURSOR, 16, bold=True)
        elif self.menu.state == MenuState.TARGET_SELECT:
            # Show note for target selection
            arcade.draw_text(
                "Select target (Left/Right, Enter)",
                panel_x + 14,
                panel_y + 10,
                COLOR_TEXT,
                12,
            )

    def _draw_target_cursor(self, x: float, y: float):
        # Simple triangle cursor pointing down
        arcade.draw_triangle_filled(x, y, x - 12, y + 18, x + 12, y + 18, COLOR_CURSOR)

    # --- Input handling ---

    def on_key_press(self, symbol: int, modifiers: int):
        if self.menu.state == MenuState.MENU:
            if symbol in (arcade.key.UP, arcade.key.W):
                self.menu.move_up()
            elif symbol in (arcade.key.DOWN, arcade.key.S):
                self.menu.move_down()
            elif symbol in (arcade.key.ENTER, arcade.key.SPACE):
                try:
                    result = self.menu.confirm(targets=self._alive_targets_for_menu())
                except ValueError as exc:
                    self._message = str(exc)
                    logger.warning("Confirm failed: %s", exc)
                    return
                if result:
                    self._handle_action_result(result)
                    # Ready for next selection
                    self.menu.reset()
            # No cancel in root menu

        elif self.menu.state == MenuState.TARGET_SELECT:
            if symbol in (arcade.key.LEFT, arcade.key.A):
                self.menu.move_left()
            elif symbol in (arcade.key.RIGHT, arcade.key.D):
                self.menu.move_right()
            elif symbol in (arcade.key.ENTER, arcade.key.SPACE):
                result = self.menu.confirm()
                if result:
                    self._handle_action_result(result)
                    # Ready for next selection
                    self.menu.reset()
            elif symbol in (arcade.key.ESCAPE, arcade.key.BACKSPACE):
                cancelled = self.menu.cancel()
                if cancelled:
                    self._message = "Selection cancelled"

    # --- Helpers ---

    def _alive_targets_for_menu(self) -> List[Target]:
        return [Target(id=e.id, name=e.name, alive=e.alive) for e in self.enemies if e.alive]

    def _handle_action_result(self, result) -> None:
        # Convert SelectionResult into an Action and log it.
        action = Action(command=result.command, target_id=result.target_id)
        self._action_log.append(action)
        if action.command in (Command.ATTACK, Command.SKILL) and action.target_id:
            # Fake: on attack, mark target dead to show visual change
            for e in self.enemies:
                if e.id == action.target_id:
                    e.alive = False
                    break
            self._message = f"{action.command.value} queued on {action.target_id}"
        else:
            self._message = f"{action.command.value} selected"
        logger.info("Action: %s", action)


class CombatWindow(arcade.Window):
    """Simple window to host the CombatView for manual testing."""

    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, TITLE, resizable=False)
        self.view = CombatView()
        self.show_view(self.view)


def main():
    """Launch a window with the combat UI skeleton.

    This is primarily for local/manual verification and is not used in tests.
    """
    logging.basicConfig(level=logging.INFO)
    window = CombatWindow()
    arcade.run()


if __name__ == "__main__":
    main()
