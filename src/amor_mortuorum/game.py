from __future__ import annotations

import logging
import random
from typing import List, Tuple

import arcade

from .config import WORLD, MINIMAP
from .minimap import MinimapModel, MinimapRenderer

logger = logging.getLogger(__name__)


class Tile:
    WALL = 0
    ROOM = 1


class DungeonMap:
    """Very simple dungeon generator for demonstration/testing purposes.

    - Generates a grid with random rectangular rooms and basic corridors.
    - Provides collision (walkable) and room queries.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: List[List[int]] = [[Tile.WALL for _ in range(height)] for _ in range(width)]
        self.rooms: List[Tuple[int, int, int, int]] = []  # x, y, w, h
        self._generate()

    def _carve_room(self, x: int, y: int, w: int, h: int) -> None:
        for cx in range(x, min(self.width, x + w)):
            for cy in range(y, min(self.height, y + h)):
                self.grid[cx][cy] = Tile.ROOM

    def _carve_corridor_h(self, x1: int, x2: int, y: int) -> None:
        if x2 < x1:
            x1, x2 = x2, x1
        for x in range(x1, x2 + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[x][y] = Tile.ROOM

    def _carve_corridor_v(self, y1: int, y2: int, x: int) -> None:
        if y2 < y1:
            y1, y2 = y2, y1
        for y in range(y1, y2 + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[x][y] = Tile.ROOM

    def _generate(self) -> None:
        rng = random.Random(1337)
        max_rooms = 12
        min_size, max_size = 4, 10

        for _ in range(max_rooms):
            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            x = rng.randint(1, max(1, self.width - w - 1))
            y = rng.randint(1, max(1, self.height - h - 1))

            # Simple overlap check
            overlaps = False
            for rx, ry, rw, rh in self.rooms:
                if (x < rx + rw and x + w > rx and y < ry + rh and y + h > ry):
                    overlaps = True
                    break
            if overlaps:
                continue

            self._carve_room(x, y, w, h)
            self.rooms.append((x, y, w, h))

        # Connect rooms with simple corridors
        for i in range(1, len(self.rooms)):
            x1, y1, w1, h1 = self.rooms[i - 1]
            x2, y2, w2, h2 = self.rooms[i]
            cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
            cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2
            if random.random() < 0.5:
                self._carve_corridor_h(cx1, cx2, cy1)
                self._carve_corridor_v(cy1, cy2, cx2)
            else:
                self._carve_corridor_v(cy1, cy2, cx1)
                self._carve_corridor_h(cx1, cx2, cy2)

        # Ensure at least one room exists
        if not self.rooms:
            # Carve a small room in the center
            cx, cy = self.width // 2 - 2, self.height // 2 - 2
            self._carve_room(cx, cy, 4, 4)
            self.rooms.append((cx, cy, 4, 4))

    def is_walkable(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[x][y] == Tile.ROOM

    def is_room(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[x][y] == Tile.ROOM


class DungeonGame(arcade.Window):
    """Main game window including simple world rendering and a minimap overlay."""

    def __init__(self, width: int = 960, height: int = 640, title: str = "Amor Mortuorum"):  # noqa: D401
        super().__init__(width, height, title, resizable=True)
        arcade.set_background_color(arcade.color.BLACK)

        # World
        self.world = DungeonMap(WORLD.width, WORLD.height)
        # Player spawns at the center of the first room
        rx, ry, rw, rh = self.world.rooms[0]
        self.player_x = rx + rw // 2
        self.player_y = ry + rh // 2

        # Minimap
        self.minimap_model = MinimapModel(self.world.width, self.world.height)
        self.minimap_renderer = MinimapRenderer(self.minimap_model)
        self.minimap_renderer.resize(self.width, self.height)

        # Exploration: reveal starting tile and immediate neighbors
        self._reveal_around_player(radius=2)

        # Camera for main world display
        self.camera = arcade.Camera(self.width, self.height)

    def _reveal_around_player(self, radius: int = 2) -> None:
        coords = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x, y = self.player_x + dx, self.player_y + dy
                if self.world.is_room(x, y):
                    coords.append((x, y))
        self.minimap_model.reveal_many(coords)

    def on_draw(self):  # noqa: D401
        self.clear()
        self.camera.use()

        # Simple main view: draw rooms and player (for demo)
        ts = WORLD.tile_px
        for x in range(self.world.width):
            for y in range(self.world.height):
                left = x * ts
                bottom = y * ts
                if self.world.grid[x][y] == Tile.ROOM:
                    arcade.draw_lrtb_rectangle_filled(left, left + ts, bottom + ts, bottom, (30, 30, 38))
                else:
                    arcade.draw_lrtb_rectangle_filled(left, left + ts, bottom + ts, bottom, (8, 8, 10))

        # Player
        px = self.player_x * ts + ts / 2
        py = self.player_y * ts + ts / 2
        arcade.draw_circle_filled(px, py, ts / 3, (200, 200, 230))

        # Minimap overlay in top-right corner
        self.minimap_renderer.draw(player_pos=(self.player_x, self.player_y), is_room=self.world.is_room)

    def on_key_press(self, symbol: int, modifiers: int):  # noqa: D401
        if symbol in (arcade.key.W, arcade.key.UP):
            self._attempt_move(0, 1)
        elif symbol in (arcade.key.S, arcade.key.DOWN):
            self._attempt_move(0, -1)
        elif symbol in (arcade.key.A, arcade.key.LEFT):
            self._attempt_move(-1, 0)
        elif symbol in (arcade.key.D, arcade.key.RIGHT):
            self._attempt_move(1, 0)
        elif symbol == arcade.key.M:
            self.minimap_renderer.toggle()
        elif symbol == arcade.key.ESCAPE:
            arcade.close_window()

    def _attempt_move(self, dx: int, dy: int) -> None:
        nx, ny = self.player_x + dx, self.player_y + dy
        if self.world.is_walkable(nx, ny):
            self.player_x, self.player_y = nx, ny
            # Reveal as the player explores
            self._reveal_around_player(radius=2)

    def on_resize(self, width: int, height: int):  # noqa: D401
        super().on_resize(width, height)
        try:
            self.camera.resize(width, height)
        except Exception as exc:  # pragma: no cover - defensive: arcade versions differ
            logger.debug("Camera resize failed (non-fatal): %s", exc)
        # Update the minimap layout; must never crash
        try:
            self.minimap_renderer.resize(width, height)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Minimap resize error: %s", exc)


def run() -> None:
    """Run the demo game with a minimap that can be toggled with 'M'."""
    logging.basicConfig(level=logging.INFO)
    game = DungeonGame()
    arcade.run()
