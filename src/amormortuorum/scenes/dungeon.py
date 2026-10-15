"""One dungeon floor: tile rendering, movement, chests, stairs, portal, encounters."""
from __future__ import annotations

import logging
from typing import Dict, Optional

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.combat import Battle, Outcome
from ..systems.encounters import combat_rng, encounter_rng, roll_formation, step_encounter
from ..systems.entities import Enemy
from ..systems.fov import Visibility
from ..systems.hub import GraveyardHub
from ..systems.loot import roll_chest, roll_chest_gold
from ..systems.procgen import (
    KEY_ITEM_ID,
    TILE_SIZE,
    FloorMap,
    Pos,
    Tile,
    generate_floor,
    trap_damage,
)
from ..systems.progression import sync_level
from ..systems.rng import chest_rng
from ..ui.hud import Hud
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui.minimap import Minimap

logger = logging.getLogger(__name__)

ALPHA_VISIBLE = 255
ALPHA_EXPLORED = 90

COLOR_WALL = (38, 38, 50)
COLOR_FLOOR = (92, 92, 108)
COLOR_STAIRS = (240, 240, 250)
COLOR_CHEST = (214, 170, 60)
COLOR_PORTAL = (0, 150, 150)
COLOR_PLAYER = (248, 248, 255)
COLOR_DOOR_LOCKED = (140, 90, 40)
COLOR_DOOR_OPEN = (70, 62, 52)
COLOR_KEY = (180, 120, 230)
COLOR_TRAP = (200, 60, 60)
COLOR_BOSS_STAIRS = (190, 50, 120)

MOVES: Dict[str, Pos] = {
    "move_up": (0, 1),
    "move_down": (0, -1),
    "move_left": (-1, 0),
    "move_right": (1, 0),
}


def tile_center(pos: Pos) -> tuple[float, float]:
    x, y = pos
    return (x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2)


class DungeonScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.state = app.state
        self.run = app.state.run
        self.data = app.state.data
        self.fmap: Optional[FloorMap] = None
        self.pos: Pos = (0, 0)
        self.tiles = arcade.SpriteList()
        self.features = arcade.SpriteList()
        self.player = arcade.SpriteList()
        self._feature_sprites: Dict[Pos, arcade.Sprite] = {}
        self._door_sprites: Dict[Pos, arcade.Sprite] = {}
        self._tile_sprites: Dict[Pos, arcade.Sprite] = {}
        self._player_sprite: Optional[arcade.Sprite] = None
        self.vis = Visibility()
        self.minimap: Optional[Minimap] = None
        self.camera: Optional[arcade.Camera2D] = None
        self.hud: Optional[Hud] = None
        self.active_battle: Optional[Battle] = None
        self._boss_battle = False
        self.paused = False
        self.pause_menu = VerticalMenu()
        self._pause_view: Optional[MenuView] = None
        self._pause_title: Optional[arcade.Text] = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        run = self.run
        self.fmap = generate_floor(run.seed, run.floor)
        self.pos = self.fmap.start
        self._chest_rng = chest_rng(run.seed, run.floor)
        self._enc_rng = encounter_rng(run.seed, run.floor)
        self._build_sprites()
        self.minimap = Minimap(self.fmap, self.vis, self.app)
        self._refresh_visibility(initial=True)
        self.camera = arcade.Camera2D()
        self.hud = Hud(self.app)
        self.hud.push(f"Floor B{run.floor}. Find the stairs.")
        boss = self.data.boss_for_floor(run.floor)
        if boss is not None and self.fmap.stairs_locked:
            self.hud.push(f"{boss.name} guards the way down.")
        if self.fmap.doors:
            self.hud.push("Heavy doors seal the way down. A key must be hidden here.")
        if self.fmap.portal is not None:
            self.hud.push("A pale light flickers somewhere on this floor...")
        self._pause_title = arcade.Text(
            "Paused", 0, 0, color=arcade.color.GHOST_WHITE, font_size=28,
            anchor_x="center", anchor_y="center",
        )
        self.pause_menu.set_items(
            [
                MenuItem("Resume", self._toggle_pause),
                MenuItem("Bag & Equipment", self._open_inventory, hint="Also: Tab"),
                MenuItem(
                    "Abandon run", self._abandon_run,
                    hint="Ends the run. Relics and the Crypt persist.",
                ),
            ],
            keep_selection=False,
        )
        self._pause_view = MenuView(self.pause_menu, 0, 0, font_size=20, anchor_x="center")
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        if self.camera is not None:
            self.camera.match_window()
        if self.hud is not None:
            self.hud.on_resize(width, height)
        if self.minimap is not None:
            self.minimap.on_resize(width, height)
        if self._pause_title is not None:
            self._pause_title.position = (width / 2, height / 2 + 60)
        if self._pause_view is not None:
            self._pause_view.set_position(width / 2, height / 2)

    def on_resume(self):
        super().on_resume()
        battle = self.active_battle
        self.active_battle = None
        was_boss, self._boss_battle = self._boss_battle, False
        if battle is None:
            return
        if battle.outcome is Outcome.VICTORY:
            xp, gold = battle.rewards()
            self.hud.push(f"Victory. +{xp} XP, +{gold} gold.")
            for up in sync_level(self.run.leader, self.data):
                self.hud.push(up.describe())
            if was_boss:
                self._on_boss_defeated()
        elif battle.outcome is Outcome.FLED:
            self.hud.push("You escaped.")
        elif battle.outcome is Outcome.DEFEAT:
            self._on_party_defeated()

    # World building

    def _build_sprites(self) -> None:
        fmap = self.fmap
        self.tiles = arcade.SpriteList(capacity=fmap.width * fmap.height)
        self._door_sprites = {}
        for y, row in enumerate(fmap.tiles):
            for x, tile in enumerate(row):
                if tile == Tile.DOOR:
                    color = COLOR_DOOR_LOCKED if fmap.doors.get((x, y)) else COLOR_DOOR_OPEN
                else:
                    color = COLOR_FLOOR if tile == Tile.FLOOR else COLOR_WALL
                cx, cy = tile_center((x, y))
                sprite = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, cx, cy, color)
                sprite.alpha = 0
                self.tiles.append(sprite)
                self._tile_sprites[(x, y)] = sprite
                if tile == Tile.DOOR:
                    self._door_sprites[(x, y)] = sprite
        self.features = arcade.SpriteList()
        self._feature_sprites = {}
        stairs_color = COLOR_BOSS_STAIRS if fmap.stairs_locked else COLOR_STAIRS
        self._add_feature(fmap.stairs, stairs_color, 22)
        for pos in fmap.chests:
            self._add_feature(pos, COLOR_CHEST, 18)
        for pos in fmap.keys:
            self._add_feature(pos, COLOR_KEY, 14)
        for pos, trap in fmap.traps.items():
            if trap.revealed:
                self._add_feature(pos, COLOR_TRAP, 12)
        if fmap.portal is not None:
            self._add_feature(fmap.portal, COLOR_PORTAL, 26)
        self.player = arcade.SpriteList()
        cx, cy = tile_center(self.pos)
        self._player_sprite = arcade.SpriteSolidColor(20, 20, cx, cy, COLOR_PLAYER)
        self.player.append(self._player_sprite)

    def _add_feature(self, pos: Pos, color, size: int) -> None:
        cx, cy = tile_center(pos)
        sprite = arcade.SpriteSolidColor(size, size, cx, cy, color)
        sprite.alpha = self._alpha_for(pos)
        self.features.append(sprite)
        self._feature_sprites[pos] = sprite

    # Fog of war

    def _alpha_for(self, pos: Pos) -> int:
        state = self.vis.state(pos)
        if state == "visible":
            return ALPHA_VISIBLE
        if state == "explored":
            return ALPHA_EXPLORED
        return 0

    def _refresh_visibility(self, initial: bool = False) -> None:
        changed = self.vis.update(self.fmap, self.pos)
        cells = self._tile_sprites.keys() if initial else changed
        for pos in cells:
            alpha = self._alpha_for(pos)
            tile = self._tile_sprites.get(pos)
            if tile is not None:
                tile.alpha = alpha
            feature = self._feature_sprites.get(pos)
            if feature is not None:
                feature.alpha = alpha
        if self.minimap is not None:
            self.minimap.refresh(cells)

    # Movement and interaction

    def _try_move(self, dx: int, dy: int) -> None:
        nx, ny = self.pos[0] + dx, self.pos[1] + dy
        if self.fmap.is_locked_door(nx, ny):
            self._try_unlock((nx, ny))
            return
        if not self.fmap.is_walkable(nx, ny):
            return
        self.pos = (nx, ny)
        self._player_sprite.position = tile_center(self.pos)
        self._refresh_visibility()
        self.run.steps_since_encounter += 1
        self._on_step()

    def _try_unlock(self, pos: Pos) -> None:
        leader = self.run.leader
        key = self.data.item(KEY_ITEM_ID)
        if not leader.inventory.has(key.id):
            self.hud.push("A locked door. It needs a Catacomb Key.")
            return
        leader.inventory.remove(key, 1)
        self.fmap.unlock_door(pos)
        sprite = self._door_sprites.get(pos)
        if sprite is not None:
            sprite.color = COLOR_DOOR_OPEN
        self._refresh_visibility()  # an open door no longer blocks sight
        if self.minimap is not None:
            self.minimap.refresh([pos])
        self.hud.push("The key turns. The door swings open.")

    def _on_step(self) -> None:
        if self.fmap.pickup_key(self.pos):
            sprite = self._feature_sprites.pop(self.pos, None)
            if sprite is not None:
                sprite.remove_from_sprite_lists()
            try:
                self.run.leader.inventory.add(self.data.item(KEY_ITEM_ID), 1)
                self.hud.push("Found a Catacomb Key.")
            except AmorError:
                self.fmap.keys.add(self.pos)
                self._add_feature(self.pos, COLOR_KEY, 14)
                self.hud.push("A key, but you cannot carry more.")
        trap = self.fmap.trigger_trap(self.pos)
        if trap is not None:
            self._add_feature(self.pos, COLOR_TRAP, 12)
            dmg = self.run.leader.take_damage(trap_damage(trap.kind, self.run.floor))
            noun = "Spikes shoot up" if trap.kind == "spikes" else "Darts hiss from the wall"
            self.hud.push(f"{noun}! You take {dmg} damage.")
            if not self.run.alive:
                self._on_party_defeated(cause=f"a {trap.kind} trap")
                return
        feature = self.fmap.feature_at(*self.pos)
        if feature == "chest":
            self._open_chest()
        elif feature == "stairs" and self.fmap.stairs_locked:
            self.hud.push("Something ancient blocks the stairs. Press Enter to face it.")
        elif feature == "stairs":
            self.hud.push("Stairs down. Press Enter to descend.")
        elif feature == "portal":
            self.hud.push("A portal to the Graveyard. Press Enter to step through.")
        if step_encounter(self._enc_rng, self.run.floor, self.run.steps_since_encounter, self.data):
            self._start_encounter()

    def _open_chest(self) -> None:
        self.fmap.remove_chest(self.pos)
        sprite = self._feature_sprites.pop(self.pos, None)
        if sprite is not None:
            sprite.remove_from_sprite_lists()
        leader = self.run.leader
        gold = roll_chest_gold(self._chest_rng, self.run.floor)
        if gold is not None:
            leader.add_gold(gold)
            self.hud.push(f"The chest holds {gold} gold.")
            return
        item = roll_chest(self._chest_rng, self.run.floor, self.data)
        try:
            leader.inventory.add(item, 1)
            self.hud.push(f"Found {item.name} ({item.quality}).")
        except AmorError:
            self.hud.push(f"Found {item.name}, but your bag cannot hold it.")

    def _start_encounter(self) -> None:
        from .combat import CombatScene

        enemies = roll_formation(self._enc_rng, self.run.floor, self.data)
        rng = combat_rng(self.run.seed, self.run.floor, self.run.encounters)
        self.run.encounters += 1
        self.run.steps_since_encounter = 0
        self.active_battle = Battle(self.run.party, enemies, rng, self.data)
        names = ", ".join(e.name for e in enemies)
        logger.info("Encounter on B%d: %s", self.run.floor, names)
        self.manager.push(CombatScene(self.app, self.active_battle))

    def _start_boss(self) -> None:
        from .combat import CombatScene

        boss = self.data.boss_for_floor(self.run.floor)
        if boss is None:  # a boss floor without data: just unlock
            self.fmap.stairs_locked = False
            return
        enemies = [Enemy.from_def(self.data.enemy(eid)) for eid in boss.enemies]
        rng = combat_rng(self.run.seed, self.run.floor, 1000 + self.run.encounters)
        self.run.encounters += 1
        self.run.steps_since_encounter = 0
        self.active_battle = Battle(self.run.party, enemies, rng, self.data)
        self._boss_battle = True
        logger.info("Boss fight on B%d: %s", self.run.floor, boss.name)
        self.hud.push(f"{boss.name} rises to meet you.")
        self.manager.push(CombatScene(self.app, self.active_battle))

    def _on_boss_defeated(self) -> None:
        from .run_summary import RunSummaryScene

        boss = self.data.boss_for_floor(self.run.floor)
        self.fmap.stairs_locked = False
        stairs = self._feature_sprites.get(self.fmap.stairs)
        if stairs is not None:
            stairs.color = COLOR_STAIRS
        meta = self.state.meta
        if boss is not None and boss.relic_id and not meta.relics.has(boss.relic_id):
            meta.relics.add(boss.relic_id)
            relic = next((r for r in self.data.relics if r.id == boss.relic_id), None)
            name = relic.name if relic else boss.relic_id
            self.hud.push(f"A Relic of the Veil: {name}.")
        meta.deepest_floor = max(meta.deepest_floor, self.run.floor)
        self.state.save_manager.save_meta(meta)
        if boss is not None and boss.final:
            summary = self.run.summary(cause="reached the bottom of the Veil", victory=True)
            self._hub().end_run(self.run)
            self.manager.replace(
                RunSummaryScene(
                    self.app, summary, "The Heart of Oblivion stills. The dead may finally rest."
                )
            )
            return
        self.hud.push("The way down is open.")

    def _interact(self) -> None:
        feature = self.fmap.feature_at(*self.pos)
        if feature == "stairs" and self.fmap.stairs_locked:
            self._start_boss()
        elif feature == "stairs":
            self.run.descend()
            self.manager.replace(DungeonScene(self.app))
        elif feature == "portal":
            from .graveyard import GraveyardScene

            self.run.in_graveyard = True
            self.manager.replace(GraveyardScene(self.app))

    # Death and pause

    def _hub(self) -> GraveyardHub:
        return GraveyardHub(self.state.save_manager, self.data, meta=self.state.meta)

    def _on_party_defeated(self, cause: str = "fell in battle") -> None:
        from .run_summary import RunSummaryScene

        hub = self._hub()
        result = self.run.on_death(self.state.meta, self.data)
        if result.revived:
            self.state.save_manager.save_meta(self.state.meta)
            summary = self.run.summary(cause=cause, revived=True)
        else:
            summary = self.run.summary(cause=cause, revived=False)
            hub.end_run(self.run)
        self.manager.replace(RunSummaryScene(self.app, summary, result.message))

    def _toggle_pause(self) -> None:
        self.paused = not self.paused

    def _open_inventory(self) -> None:
        from .inventory import InventoryScene

        self.paused = False
        self.manager.push(InventoryScene(self.app))

    def _abandon_run(self) -> None:
        from .main_menu import MainMenuScene

        self._hub().end_run(self.run)
        self.state.run = None
        self.manager.pop_until(MainMenuScene)

    # Rendering and input

    def draw(self):
        if self.camera is not None:
            self.camera.position = self._player_sprite.position
            self.camera.use()
        self.tiles.draw()
        self.features.draw()
        self.player.draw()
        self.app.default_camera.use()
        if self.hud is not None:
            self.hud.draw(self.run, extra=f"Steps {self.run.steps_since_encounter}   [M] map")
        if self.minimap is not None:
            self.minimap.draw(self.pos)
        if self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 170))
            self._pause_title.draw()
            self._pause_view.draw()

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.paused:
            if self.pause_menu.handle_actions(actions):
                return True
            if "cancel" in actions:
                self._toggle_pause()
                return True
            return False
        for action, (dx, dy) in MOVES.items():
            if action in actions:
                self._try_move(dx, dy)
                return True
        if "confirm" in actions:
            self._interact()
            return True
        if "menu" in actions:
            self._open_inventory()
            return True
        if "map" in actions:
            if self.minimap is not None:
                self.minimap.toggle()
            return True
        if "cancel" in actions or "pause" in actions:
            self._toggle_pause()
            return True
        return False
