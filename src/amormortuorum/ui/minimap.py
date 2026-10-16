"""Minimap overlay: explored tiles plus icons for features the player has seen."""
from __future__ import annotations

from typing import Dict, Iterable, Sequence

import arcade

from ..systems.fov import Visibility
from ..systems.procgen import FloorMap, Pos, Tile

SCALE = 4
MARGIN = 12
TOP_OFFSET = 100  # below the HUD panel

C_FLOOR = (170, 170, 190)
C_WALL = (60, 60, 75)
C_DOOR = (160, 105, 50)
C_DOOR_OPEN = (110, 95, 80)
C_BACK = (0, 0, 0, 170)
ICONS = {
    "stairs": (255, 255, 255),
    "chest": (230, 185, 70),
    "portal": (0, 200, 200),
    "key": (190, 130, 240),
    "trap": (220, 70, 70),
    "player": (255, 255, 255),
    "monster": (240, 90, 90),
}
ALPHA_VISIBLE = 255
ALPHA_EXPLORED = 120


class Minimap:
    def __init__(self, fmap: FloorMap, visibility: Visibility, app) -> None:
        self.fmap = fmap
        self.vis = visibility
        self.app = app
        self.enabled = True
        self.ox = 0.0
        self.oy = 0.0
        self._tiles = arcade.SpriteList(capacity=fmap.width * fmap.height)
        self._by_pos: Dict[Pos, arcade.Sprite] = {}
        for y, row in enumerate(fmap.tiles):
            for x, tile in enumerate(row):
                color = C_FLOOR if tile == Tile.FLOOR else C_DOOR if tile == Tile.DOOR else C_WALL
                sprite = arcade.SpriteSolidColor(SCALE, SCALE, 0, 0, color)
                sprite.alpha = 0
                self._tiles.append(sprite)
                self._by_pos[(x, y)] = sprite
        self.on_resize(app.width, app.height)
        self.refresh(self._by_pos.keys())

    # Layout

    @property
    def width_px(self) -> int:
        return self.fmap.width * SCALE

    @property
    def height_px(self) -> int:
        return self.fmap.height * SCALE

    def on_resize(self, width: int, height: int) -> None:
        self.ox = width - MARGIN - self.width_px
        self.oy = height - TOP_OFFSET - self.height_px
        for (x, y), sprite in self._by_pos.items():
            sprite.position = self._screen(x, y)

    def _screen(self, x: int, y: int) -> tuple[float, float]:
        return (self.ox + x * SCALE + SCALE / 2, self.oy + y * SCALE + SCALE / 2)

    # State

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def refresh(self, cells: Iterable[Pos]) -> None:
        """Update alpha for ``cells`` from the visibility state."""
        for pos in cells:
            sprite = self._by_pos.get(pos)
            if sprite is None:
                continue
            state = self.vis.state(pos)
            sprite.alpha = (
                ALPHA_VISIBLE if state == "visible"
                else ALPHA_EXPLORED if state == "explored"
                else 0
            )
            if self.fmap.tile(*pos) == Tile.DOOR:
                sprite.color = C_DOOR if self.fmap.doors.get(pos) else C_DOOR_OPEN

    # Drawing

    def _icon(self, pos: Pos, color, size: float = SCALE, shape: str = "square") -> None:
        """Draw a feature marker. Shapes differ per feature so colour is never the only cue:
        stairs = hollow square, chest = filled square, portal = ring, key = diamond,
        trap = cross, player = filled circle, monster = triangle."""
        cx, cy = self._screen(*pos)
        half = size / 2
        if shape == "square":
            arcade.draw_lbwh_rectangle_filled(cx - half, cy - half, size, size, color)
        elif shape == "hollow":
            arcade.draw_lbwh_rectangle_outline(cx - half, cy - half, size, size, color, 1)
        elif shape == "ring":
            arcade.draw_circle_outline(cx, cy, half, color, 1)
        elif shape == "circle":
            arcade.draw_circle_filled(cx, cy, half, color)
        elif shape == "diamond":
            arcade.draw_polygon_filled(
                [(cx, cy + half), (cx + half, cy), (cx, cy - half), (cx - half, cy)], color
            )
        elif shape == "cross":
            arcade.draw_line(cx - half, cy - half, cx + half, cy + half, color, 1)
            arcade.draw_line(cx - half, cy + half, cx + half, cy - half, color, 1)
        elif shape == "triangle":
            arcade.draw_polygon_filled(
                [(cx, cy + half), (cx + half, cy - half), (cx - half, cy - half)], color
            )

    def draw(self, player_pos: Pos, monsters: Sequence[Pos] = ()) -> None:
        if not self.enabled:
            return
        arcade.draw_lbwh_rectangle_filled(
            self.ox - 4, self.oy - 4, self.width_px + 8, self.height_px + 8, C_BACK
        )
        self._tiles.draw()
        fmap = self.fmap
        explored = self.vis.explored
        if fmap.stairs in explored:
            self._icon(fmap.stairs, ICONS["stairs"], SCALE + 3, shape="hollow")
        for pos in fmap.chests:
            if pos in explored:
                self._icon(pos, ICONS["chest"], SCALE + 1, shape="square")
        for pos in fmap.keys:
            if pos in explored:
                self._icon(pos, ICONS["key"], SCALE + 3, shape="diamond")
        for pos, trap in fmap.traps.items():
            if trap.revealed and pos in explored:
                self._icon(pos, ICONS["trap"], SCALE + 2, shape="cross")
        if fmap.portal is not None and fmap.portal in explored:
            self._icon(fmap.portal, ICONS["portal"], SCALE + 4, shape="ring")
        for pos in monsters:
            self._icon(pos, ICONS["monster"], SCALE + 3, shape="triangle")
        self._icon(player_pos, ICONS["player"], SCALE + 3, shape="circle")
