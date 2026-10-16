"""One dungeon floor: tile rendering, movement, chests, stairs, portal, encounters."""
from __future__ import annotations

import logging
from typing import Dict, Optional

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.combat import Battle, Outcome
from ..systems.entities import Enemy
from ..systems.encounters import (
    boss_formation,
    combat_rng,
    encounter_rng,
    roll_formation,
    step_encounter,
)
from ..systems.fov import Visibility
from ..systems.hub import GraveyardHub
from ..systems.loot import roll_chest, roll_chest_gold, roll_relic
from ..systems.monsters import (
    NOISE_RADIUS,
    TRAP_NOISE_RADIUS,
    Monster,
    daze,
    make_noise,
    maybe_respawn,
    monster_at,
    monster_rng,
    remove_monster,
    spawn_monsters,
    step_monsters,
)
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
from ..systems.relics import apply_passives
from ..systems.stats import bump, check_achievements, record_max
from ..systems.rng import chest_rng
from ..ui.hud import Hud
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui import frame, pixelart, tiles
from ..ui.minimap import Minimap
from ..ui.theme import fs

logger = logging.getLogger(__name__)

ALPHA_VISIBLE = 255

COLOR_STAIRS = (255, 255, 255)  # tint: plain texture
COLOR_BOSS_STAIRS = (190, 50, 120)
COLOR_MONSTER = (170, 60, 70)
COLOR_MONSTER_CHASE = (235, 80, 80)
COLOR_MONSTER_SLEEP = (120, 70, 95)
COLOR_MONSTER_FLEE = (235, 170, 90)
TINT_SLEEP = (150, 150, 185)
TINT_CHASE = (255, 170, 170)
TINT_FLEE = (255, 220, 160)
TINT_PLAIN = (255, 255, 255)
BADGE = 7  # px: kind badge drawn in a tile corner
SPRITE_SCALE = TILE_SIZE / pixelart.RENDER_PX
WORLD_ZOOM = 2.0          # 32 px art shown at 64 px: chunky 16-bit pixels
IDLE_FRAME_TIME = 0.5     # seconds per idle animation frame
MOVE_TIME = 0.16          # seconds a step takes on screen
STRIDE_PERIOD = 0.32      # seconds for a full walk cycle while moving
HOLD_DELAY = 0.22         # seconds a direction must be held before auto-walking
PORTAL_FRAME_TIME = 0.12
TORCH = (255, 244, 224)   # light colour next to the party
TORCH_FAR = (190, 200, 235)  # light colour at the edge of sight
LIGHT_MIN = 0.42          # brightness at the edge of the field of view
EXPLORED_TINT = (62, 64, 96)  # remembered tiles: dim and cold
NOTICE_VERB = {"hunter": "prowls", "guard": "stands watch", "skittish": "skulks"}
ENGAGE_VERB = {"hunter": "engage", "guard": "challenge", "skittish": "corner"}

MOVES: Dict[str, Pos] = {
    "move_up": (0, 1),
    "move_down": (0, -1),
    "move_left": (-1, 0),
    "move_right": (1, 0),
}


def tile_center(pos: Pos) -> tuple[float, float]:
    x, y = pos
    return (x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2)


def monster_color(m: Monster):
    """Marker colour by state: dull asleep, red idle, bright red hunting, amber fleeing."""
    if m.chasing:
        return COLOR_MONSTER_CHASE
    if m.fleeing:
        return COLOR_MONSTER_FLEE
    if m.asleep:
        return COLOR_MONSTER_SLEEP
    return COLOR_MONSTER


def light_at(dist: float, radius: int) -> tuple[int, int, int]:
    """Torchlight falloff: warm and bright near the party, cool and dim at the edge."""
    t = max(0.0, min(1.0, dist / (radius + 1)))
    f = 1.0 - (1.0 - LIGHT_MIN) * t
    return tuple(
        int((a * (1 - t) + b * t) * f) for a, b in zip(TORCH, TORCH_FAR)
    )  # type: ignore[return-value]


def blend(a: tuple, b: tuple) -> tuple[int, int, int]:
    """Multiply two RGB tints."""
    return (a[0] * b[0] // 255, a[1] * b[1] // 255, a[2] * b[2] // 255)


def monster_tint(m: Monster):
    """Sprite tint by state: dull asleep, reddish hunting, warm while fleeing."""
    if m.chasing:
        return TINT_CHASE
    if m.fleeing:
        return TINT_FLEE
    if m.asleep:
        return TINT_SLEEP
    return TINT_PLAIN


def monster_points(m: Monster) -> list[tuple[float, float]]:
    """Kind badge in the tile's top-right corner, so colour is never the only cue:
    hunter = triangle, guard = square, skittish = diamond."""
    tx, ty = tile_center(m.pos)
    cx, cy = tx + TILE_SIZE / 2 - BADGE, ty + TILE_SIZE / 2 - BADGE
    h = BADGE / 2
    if m.kind == "guard":
        return [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    if m.kind == "skittish":
        return [(cx, cy + h), (cx + h, cy), (cx, cy - h), (cx - h, cy)]
    return [(cx, cy + h), (cx + h, cy - h), (cx - h, cy - h)]


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
        self.monsters: list[Monster] = []
        self.monster_sprites = arcade.SpriteList()
        self._monster_sprites: Dict[int, arcade.Sprite] = {}
        self._engaged: Optional[Monster] = None
        self._floor_steps = 0
        self._feature_sprites: Dict[Pos, arcade.Sprite] = {}
        self._lit: set = set()
        self._anim = 0.0
        self._idle_frame = 0
        self._facing = "down"
        self._move_from: Optional[tuple] = None  # screen position a step started from
        self._move_t = 0.0                       # seconds into the current step
        self._stride = 0.0                       # seconds spent walking (cycle clock)
        self._hold = 0.0                         # seconds a direction key has been held
        self._monster_from: Dict[int, tuple] = {}  # monster id -> (from, t)
        self._monster_facing: Dict[int, str] = {}
        self._portal_frames: list = []
        self._portal_sprite: Optional[arcade.Sprite] = None
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
        self._pause_legend: Optional[arcade.Text] = None

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        run = self.run
        self.fmap = generate_floor(run.seed, run.floor)
        self.pos = self.fmap.start
        self._chest_rng = chest_rng(run.seed, run.floor)
        self._enc_rng = encounter_rng(run.seed, run.floor)
        self._mon_rng = monster_rng(run.seed, run.floor)
        self.monsters = spawn_monsters(self.fmap, run.floor, self.data, self._mon_rng)
        record_max(self.state.meta, "deepest_floor", run.floor)
        self.state.meta.deepest_floor = max(self.state.meta.deepest_floor, run.floor)
        self.vis.radius += run.leader.bonus("fov")
        self._build_sprites()
        self.minimap = Minimap(self.fmap, self.vis, self.app)
        self._refresh_visibility(initial=True)
        self.camera = arcade.Camera2D(zoom=WORLD_ZOOM)
        self.hud = Hud(self.app)
        self.hud.push(f"Floor B{run.floor}. Find the stairs.")
        self._refresh_monsters()
        boss = self.data.boss_for_floor(run.floor)
        if boss is not None and self.fmap.stairs_locked:
            self.hud.push(f"{boss.name} guards the way down.")
        if self.fmap.doors:
            self.hud.push("Heavy doors seal the way down. A key must be hidden here.")
        if self.fmap.portal is not None:
            self.hud.push("A pale light flickers somewhere on this floor...")
        self._pause_title = arcade.Text(
            "Paused", 0, 0, color=arcade.color.GHOST_WHITE, font_size=fs(28),
            anchor_x="center", anchor_y="center",
        )
        self._pause_legend = arcade.Text(
            "Markers: triangle hunts you, square guards its post, diamond runs away.  "
            "Dull = asleep, bright red = hunting, amber = fleeing.",
            0, 0, color=(150, 150, 165), font_size=fs(12), anchor_x="center", anchor_y="center",
            multiline=True, width=620, align="center",
        )
        self.pause_menu.set_items(
            [
                MenuItem("Resume", self._toggle_pause),
                MenuItem("Bag & Equipment", self._open_inventory, hint="Also: Tab"),
                MenuItem("Settings", self._open_settings, hint="Fullscreen, volumes"),
                MenuItem(
                    "Save & Quit", self._save_and_quit,
                    hint="Resume later at the start of this floor (one-shot save)",
                ),
                MenuItem(
                    "Abandon run", self._abandon_run,
                    hint="Ends the run. Relics and the Crypt persist.",
                ),
            ],
            keep_selection=False,
        )
        self._pause_view = MenuView(self.pause_menu, 0, 0, font_size=fs(20), anchor_x="center")
        self.pause_menu.sfx = self.app.audio.play
        self.app.audio.play_music("dungeon")
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
        if self._pause_legend is not None:
            self._pause_legend.position = (width / 2, height / 2 - fs(170))

    def on_resume(self):
        super().on_resume()
        battle = self.active_battle
        self.active_battle = None
        was_boss, self._boss_battle = self._boss_battle, False
        engaged, self._engaged = self._engaged, None
        self.app.audio.play_music("dungeon")
        if battle is None:
            return
        if battle.outcome is Outcome.VICTORY:
            xp, gold = battle.rewards()
            self.hud.push(f"Victory. +{xp} XP, +{gold} gold.")
            self._stat("battles_won")
            self._stat("enemies_slain", len(battle.enemies))
            self._stat("gold_earned", gold)
            for member in self.run.party:
                for up in sync_level(member, self.data):
                    self.app.audio.play("level_up")
                    self.hud.push(f"{member.name}: {up.describe()}")
            if was_boss:
                self._on_boss_defeated()
            if engaged is not None:
                if engaged.asleep:
                    self._stat("ambushes")
                if engaged.bounty > 0:
                    self._stat("bounties")
                    self.run.leader.add_gold(engaged.bounty)
                    self._stat("gold_earned", engaged.bounty)
                    self.hud.push(f"The {engaged.name} drops its hoard: +{engaged.bounty} gold.")
                remove_monster(self.monsters, engaged)
                self._refresh_monsters()
        elif battle.outcome is Outcome.FLED:
            self.hud.push("You escaped.")
            if engaged is not None:
                daze(engaged)
                self._refresh_monsters()
        elif battle.outcome is Outcome.DEFEAT:
            self._on_party_defeated()
            return
        self._make_noise(NOISE_RADIUS, "The din of battle carries. Something stirs.")

    # World building

    def _open(self, x: int, y: int) -> bool:
        """Is this cell floor-like (anything but solid wall)?"""
        return self.fmap.in_bounds(x, y) and self.fmap.tile(x, y) != Tile.WALL

    def _tile_texture(self, x: int, y: int, tile: Tile) -> arcade.Texture:
        """Autotile a map cell: floors get shadow bands under walls, walls get a
        brick face where floor lies below them and a lit rim on sides facing floor."""
        fmap = self.fmap
        style = fmap.style if fmap.style in tiles.STYLES else "rooms"
        if tile == Tile.DOOR:
            return tiles.texture("door_locked" if fmap.doors.get((x, y)) else "door_open", style)
        if tile != Tile.WALL:
            return tiles.floor_texture(
                style, x, y,
                shadow_top=not self._open(x, y + 1), shadow_left=not self._open(x - 1, y),
            )
        face = self._open(x, y - 1)
        rims = (self._open(x, y + 1), self._open(x + 1, y), False, self._open(x - 1, y))
        return tiles.wall_texture(style, face, rims, x, y)

    def _build_sprites(self) -> None:
        fmap = self.fmap
        self.tiles = arcade.SpriteList(capacity=fmap.width * fmap.height)
        self._door_sprites = {}
        for y, row in enumerate(fmap.tiles):
            for x, tile in enumerate(row):
                cx, cy = tile_center((x, y))
                sprite = arcade.Sprite(
                    self._tile_texture(x, y, tile), scale=SPRITE_SCALE, center_x=cx, center_y=cy
                )
                sprite.alpha = 0
                self.tiles.append(sprite)
                self._tile_sprites[(x, y)] = sprite
                if tile == Tile.DOOR:
                    self._door_sprites[(x, y)] = sprite
        self.features = arcade.SpriteList()
        self._feature_sprites = {}
        style = fmap.style if fmap.style in tiles.STYLES else "rooms"
        stairs = self._add_feature(fmap.stairs, tiles.texture("stairs", style))
        if fmap.stairs_locked:
            stairs.color = COLOR_BOSS_STAIRS
        for pos in fmap.chests:
            self._add_feature(pos, "chest")
        for pos in fmap.keys:
            self._add_feature(pos, "key")
        for pos, trap in fmap.traps.items():
            if trap.revealed:
                self._add_feature(pos, "trap")
        if fmap.portal is not None:
            self._portal_frames = tiles.portal_frames()
            self._portal_sprite = self._add_feature(fmap.portal, self._portal_frames[0])
        self.player = arcade.SpriteList()
        self._player_sprite = pixelart.sprite(
            pixelart.party_sprite_name(self.run.leader.companion_id),
            tile_center(self.pos), SPRITE_SCALE,
        )
        self.player.append(self._player_sprite)
        self.monster_sprites = arcade.SpriteList()
        self._monster_sprites = {}

    def _add_feature(self, pos: Pos, art) -> arcade.Sprite:
        """Place a feature sprite from a pixelart name or a ready texture."""
        cx, cy = tile_center(pos)
        tex = pixelart.texture(art) if isinstance(art, str) else art
        sprite = arcade.Sprite(tex, scale=SPRITE_SCALE, center_x=cx, center_y=cy)
        self._shade(sprite, pos)
        self.features.append(sprite)
        self._feature_sprites[pos] = sprite
        return sprite

    # Statistics

    def _stat(self, key: str, amount: int = 1, *, persist: bool = False) -> None:
        """Bump a lifetime counter, announce unlocks, and persist meta when asked."""
        meta = self.state.meta
        bump(meta, key, amount)
        unlocked = check_achievements(meta, self.data)
        for ach in unlocked:
            self.app.audio.play("relic")
            self.hud.push(f"Achievement: {ach.name}")
        if persist or unlocked:
            self.state.save_manager.save_meta(meta)

    # Monsters

    def _refresh_monsters(self) -> None:
        """Sync monster portraits with the model and announce first sightings."""
        alive = {m.id for m in self.monsters}
        for mid in [mid for mid in self._monster_sprites if mid not in alive]:
            self._monster_sprites.pop(mid).remove_from_sprite_lists()
        for m in self.monsters:
            sprite = self._monster_sprites.get(m.id)
            if sprite is None:
                art = pixelart.enemy_sprite_name(m.lead or m.enemies[0])
                sprite = pixelart.sprite(art, tile_center(m.pos), SPRITE_SCALE)
                self.monster_sprites.append(sprite)
                self._monster_sprites[m.id] = sprite
            target = tile_center(m.pos)
            if tuple(sprite.position) != target:
                if sprite.alpha and abs(sprite.center_x - target[0]) <= TILE_SIZE * 1.5 \
                        and abs(sprite.center_y - target[1]) <= TILE_SIZE * 1.5:
                    self._monster_from[m.id] = (tuple(sprite.position), 0.0)
                    if target[0] != sprite.center_x:
                        left = target[0] < sprite.center_x
                        self._monster_facing[m.id] = "left" if left else "right"
                else:
                    sprite.position = target
                    self._monster_from.pop(m.id, None)
            seen = m.pos in self.vis.visible
            sprite.color = blend(monster_tint(m), self._light(m.pos)) if seen else TINT_PLAIN
            sprite.alpha = ALPHA_VISIBLE if seen else 0
            if seen and not m.noticed:
                m.noticed = True
                verb = "sleeps" if m.asleep else NOTICE_VERB.get(m.kind, "prowls")
                self.hud.push(f"A {m.name} {verb} nearby.")

    def _visible_monsters(self) -> list[Monster]:
        return [m for m in self.monsters if m.pos in self.vis.visible]

    def _draw_monsters(self) -> None:
        """Portraits from the sprite list, then a kind badge per visible monster."""
        self.monster_sprites.draw(pixelated=True)
        for m in self._visible_monsters():
            arcade.draw_polygon_filled(monster_points(m), monster_color(m))

    def _make_noise(self, radius: int, message: str) -> None:
        """Wake and draw monsters within earshot of the party's tile."""
        if self.fmap is None or not self.monsters:
            return
        stirred = make_noise(self.monsters, self.fmap, self.pos, radius)
        if stirred:
            self.hud.push(message)
            self._refresh_monsters()

    def _step_monsters(self) -> None:
        """Monsters take their turn after the party's step; one may catch the party."""
        log: list = []
        caught = step_monsters(
            self.monsters, self.fmap, self.pos, self.vis.visible, self._mon_rng,
            step=self._floor_steps, player_spd=self.run.leader.effective_spd(self.data),
            log=log,
        )
        for kind, caller, joined in log:
            if kind == "bellow":
                self.hud.push(f"The {caller.name} bellows. Something answers from the dark.")
            else:
                kin = "its kin take" if len(joined) > 1 else "another takes"
                self.hud.push(f"The {caller.name} howls; {kin} up the hunt.")
        maybe_respawn(
            self.monsters, self.fmap, self.run.floor, self.pos, self.data, self._mon_rng,
            visible=self.vis.visible,
        )
        self._refresh_monsters()
        if caught is not None:
            self.hud.push(f"The {caught.name} catches you!")
            self._start_encounter(caught)

    # Fog of war

    def _alpha_for(self, pos: Pos) -> int:
        return 0 if self.vis.state(pos) == "unknown" else ALPHA_VISIBLE

    def _light(self, pos: Pos) -> tuple[int, int, int]:
        """Torchlight tint for a visible cell, by distance from the party."""
        dx, dy = pos[0] - self.pos[0], pos[1] - self.pos[1]
        return light_at((dx * dx + dy * dy) ** 0.5, self.vis.radius)

    def _shade(self, sprite: arcade.Sprite, pos: Pos) -> None:
        """Hide unknown cells, dim remembered ones, light visible ones by distance."""
        state = self.vis.state(pos)
        if state == "unknown":
            sprite.alpha = 0
            return
        sprite.alpha = ALPHA_VISIBLE
        base = self._light(pos) if state == "visible" else EXPLORED_TINT
        if sprite is self._feature_sprites.get(self.fmap.stairs) and self.fmap.stairs_locked:
            base = blend(base, COLOR_BOSS_STAIRS)
        sprite.color = base

    def _refresh_visibility(self, initial: bool = False) -> None:
        changed = self.vis.update(self.fmap, self.pos)
        visible = set(self.vis.visible)
        # Light falls off with distance, so every lit cell is re-shaded each step
        cells = set(self._tile_sprites) if initial else set(changed) | self._lit | visible
        self._lit = visible
        for pos in cells:
            tile = self._tile_sprites.get(pos)
            if tile is not None:
                self._shade(tile, pos)
            feature = self._feature_sprites.get(pos)
            if feature is not None:
                self._shade(feature, pos)
        if self.minimap is not None:
            self.minimap.refresh(changed if not initial else cells)

    # Movement and interaction

    def _try_move(self, dx: int, dy: int) -> None:
        self._facing = pixelart.facing_from(dx, dy, self._facing)
        nx, ny = self.pos[0] + dx, self.pos[1] + dy
        if self.fmap.is_locked_door(nx, ny):
            self._try_unlock((nx, ny))
            return
        if not self.fmap.is_walkable(nx, ny):
            return
        target = monster_at(self.monsters, (nx, ny))
        if target is not None:
            if target.asleep:
                self.hud.push(f"You fall upon the sleeping {target.name}.")
            else:
                verb = ENGAGE_VERB.get(target.kind, "engage")
                self.hud.push(f"You {verb} the {target.name}.")
            self._start_encounter(target)
            return
        self._move_from = tuple(self._player_sprite.position)
        self._move_t = 0.0
        self.pos = (nx, ny)
        self.app.audio.play("step")
        self._refresh_visibility()
        self._stat("steps")
        self.run.steps_since_encounter += 1
        self._floor_steps += 1
        self._on_step()
        if self.active_battle is None and self.manager.current is self:
            self._step_monsters()

    def _try_unlock(self, pos: Pos) -> None:
        leader = self.run.leader
        key = self.data.item(KEY_ITEM_ID)
        if not leader.inventory.has(key.id):
            self.app.audio.play("menu_back")
            self.hud.push("A locked door. It needs a Catacomb Key.")
            return
        leader.inventory.remove(key, 1)
        self.app.audio.play("door")
        self.fmap.unlock_door(pos)
        sprite = self._door_sprites.get(pos)
        if sprite is not None:
            style = self.fmap.style if self.fmap.style in tiles.STYLES else "rooms"
            sprite.texture = tiles.texture("door_open", style)
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
                self.app.audio.play("chest")
                self.hud.push("Found a Catacomb Key.")
            except AmorError:
                self.fmap.keys.add(self.pos)
                self._add_feature(self.pos, "key")
                self.hud.push("A key, but you cannot carry more.")
        trap = self.fmap.trigger_trap(self.pos)
        if trap is not None:
            self.app.audio.play("trap")
            self._add_feature(self.pos, "trap")
            dmg = self.run.leader.take_damage(trap_damage(trap.kind, self.run.floor))
            noun = "Spikes shoot up" if trap.kind == "spikes" else "Darts hiss from the wall"
            self.hud.push(f"{noun}! You take {dmg} damage.")
            if not self.run.alive:
                self._on_party_defeated(cause=f"a {trap.kind} trap")
                return
            self._make_noise(TRAP_NOISE_RADIUS, "The clatter echoes down the halls.")
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
            self.hud.push("Something lunges from the dark!")
            self._start_encounter()

    def _open_chest(self) -> None:
        self.fmap.remove_chest(self.pos)
        sprite = self._feature_sprites.pop(self.pos, None)
        if sprite is not None:
            sprite.remove_from_sprite_lists()
        leader = self.run.leader
        self._stat("chests_opened")
        relic = roll_relic(
            self._chest_rng, self.run.floor, self.data, self.state.meta.relics.collected
        )
        if relic is not None:
            self._gain_relic(relic.id)
            return
        gold = roll_chest_gold(self._chest_rng, self.run.floor)
        if gold is not None:
            leader.add_gold(gold)
            self._stat("gold_earned", gold)
            self.app.audio.play("gold")
            self.hud.push(f"The chest holds {gold} gold.")
            return
        item = roll_chest(self._chest_rng, self.run.floor, self.data)
        try:
            leader.inventory.add(item, 1)
            self.app.audio.play("chest")
            self.hud.push(f"Found {item.name} ({item.quality}).")
        except AmorError:
            self.hud.push(f"Found {item.name}, but your bag cannot hold it.")

    def _start_encounter(self, monster: Optional[Monster] = None) -> None:
        """Fight ``monster``'s group, or an ambush rolled from the floor's formations."""
        from .combat import CombatScene

        if monster is not None:
            enemies = [
                Enemy.from_def(self.data.enemy(eid), self.run.floor, self.data.balance)
                for eid in monster.enemies
            ]
            self._engaged = monster
        else:
            enemies = roll_formation(self._enc_rng, self.run.floor, self.data)
        rng = combat_rng(self.run.seed, self.run.floor, self.run.encounters)
        self.run.encounters += 1
        self.run.steps_since_encounter = 0
        self.active_battle = Battle(self.run.party, enemies, rng, self.data)
        names = ", ".join(e.name for e in enemies)
        logger.info("Encounter on B%d: %s", self.run.floor, names)
        title = f"Battle! {names}" if monster is not None else None
        self.manager.push(CombatScene(self.app, self.active_battle, title=title))

    def _gain_relic(self, relic_id: str) -> None:
        """Add a relic to the meta collection, persist it, and refresh passives."""
        meta = self.state.meta
        if meta.relics.has(relic_id):
            return
        meta.relics.add(relic_id)
        relic = self.data.relic(relic_id)
        self.app.audio.play("relic")
        self.hud.push(f"A Relic of the Veil: {relic.name}.")
        apply_passives(self.run, meta, self.data)
        self.state.save_manager.save_meta(meta)
        logger.info("Relic collected: %s (%d/%d)", relic_id, len(meta.relics.collected),
                    len(self.data.relics))

    def _start_boss(self) -> None:
        from .combat import CombatScene

        boss = self.data.boss_for_floor(self.run.floor)
        if boss is None:  # a boss floor without data: just unlock
            self.fmap.stairs_locked = False
            return
        enemies = boss_formation(self.run.floor, self.data)
        rng = combat_rng(self.run.seed, self.run.floor, 1000 + self.run.encounters)
        self.run.encounters += 1
        self.run.steps_since_encounter = 0
        self.active_battle = Battle(self.run.party, enemies, rng, self.data)
        self._boss_battle = True
        self.app.audio.play("boss")
        logger.info("Boss fight on B%d: %s", self.run.floor, boss.name)
        self.hud.push(f"{boss.name} rises to meet you.")
        self.manager.push(
            CombatScene(self.app, self.active_battle, title=f"{boss.name} rises to meet you")
        )

    def _on_boss_defeated(self) -> None:
        from .run_summary import RunSummaryScene

        boss = self.data.boss_for_floor(self.run.floor)
        self.fmap.stairs_locked = False
        self._stat("bosses_slain")
        stairs = self._feature_sprites.get(self.fmap.stairs)
        if stairs is not None:
            self._shade(stairs, self.fmap.stairs)
        meta = self.state.meta
        if boss is not None and boss.relic_id and not meta.relics.has(boss.relic_id):
            self._gain_relic(boss.relic_id)
        meta.deepest_floor = max(meta.deepest_floor, self.run.floor)
        self.state.save_manager.save_meta(meta)
        if boss is not None and boss.final:
            self._stat("runs_won", persist=True)
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
            self.app.audio.play("stairs")
            self.run.descend()
            self.manager.replace(DungeonScene(self.app))
        elif feature == "portal":
            from .graveyard import GraveyardScene

            self.app.audio.play("portal")
            self.run.in_graveyard = True
            self.manager.replace(GraveyardScene(self.app))

    # Death and pause

    def _hub(self) -> GraveyardHub:
        return GraveyardHub(self.state.save_manager, self.data, meta=self.state.meta)

    def _on_party_defeated(self, cause: str = "fell in battle") -> None:
        from .run_summary import RunSummaryScene

        hub = self._hub()
        result = self.run.on_death(self.state.meta, self.data)
        self._stat("deaths")
        if result.revived:
            self._stat("revives", persist=True)
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

    def _open_settings(self) -> None:
        from .settings import SettingsScene

        self.paused = False
        self.manager.push(SettingsScene(self.app))

    def _save_and_quit(self) -> None:
        from .main_menu import MainMenuScene

        self._hub().save_and_quit(self.run)
        self.state.run = None
        self.manager.pop_until(MainMenuScene)

    def _abandon_run(self) -> None:
        from .main_menu import MainMenuScene

        self._hub().end_run(self.run)
        self.state.run = None
        self.manager.pop_until(MainMenuScene)

    # Rendering and input

    def _held_direction(self) -> Optional[tuple]:
        """The (dx, dy) of a movement key currently held, if any."""
        inp = getattr(self.app, "input", None)
        if inp is None:
            return None
        for action, delta in MOVES.items():
            if inp.is_pressed(action):
                return delta
        return None

    def _animate_walkers(self, delta_time: float) -> None:
        """Slide the party and monsters between tiles; pick stride or idle frames."""
        sprite = self._player_sprite
        moving = self._move_from is not None
        if moving and sprite is not None:
            self._move_t += delta_time
            self._stride += delta_time
            t = min(1.0, self._move_t / MOVE_TIME)
            fx, fy = self._move_from
            tx, ty = tile_center(self.pos)
            sprite.position = (fx + (tx - fx) * t, fy + (ty - fy) * t)
            if t >= 1.0:
                self._move_from = None
        if sprite is not None:
            art = pixelart.party_sprite_name(self.run.leader.companion_id)
            frame = pixelart.walk_frame(self._stride, STRIDE_PERIOD) if moving else self._idle_frame
            tex = pixelart.texture(art, frame, self._facing)
            if sprite.texture is not tex:
                sprite.texture = tex
        for m in self.monsters:
            ms = self._monster_sprites.get(m.id)
            if ms is None:
                continue
            tween = self._monster_from.get(m.id)
            if tween is not None:
                start, t = tween
                t += delta_time
                k = min(1.0, t / MOVE_TIME)
                tx, ty = tile_center(m.pos)
                ms.position = (start[0] + (tx - start[0]) * k, start[1] + (ty - start[1]) * k)
                if k >= 1.0:
                    self._monster_from.pop(m.id, None)
                else:
                    self._monster_from[m.id] = (start, t)
            art = pixelart.enemy_sprite_name(m.lead or m.enemies[0])
            if m.asleep:
                frame = 0
            elif tween is not None:
                frame = pixelart.walk_frame(self._anim, STRIDE_PERIOD)
            else:
                frame = self._idle_frame
            tex = pixelart.texture(art, frame)
            if self._monster_facing.get(m.id) == "left":
                tex = self._flipped(tex)
            if ms.texture is not tex:
                ms.texture = tex

    _flip_cache: Dict[int, arcade.Texture] = {}

    def _flipped(self, tex: arcade.Texture) -> arcade.Texture:
        key = id(tex)
        out = self._flip_cache.get(key)
        if out is None:
            out = tex.flip_left_right()
            self._flip_cache[key] = out
        return out

    def update(self, delta_time: float):
        """Walk tweens and stride frames, idle breathing, the turning portal, and
        auto-walk while a direction key is held."""
        self._anim += delta_time
        self._idle_frame = int(self._anim / IDLE_FRAME_TIME) % 2
        self._animate_walkers(delta_time)
        held = self._held_direction() if not self.paused else None
        if held is None:
            self._hold = 0.0
            if self._move_from is None:
                self._stride = 0.0
        else:
            self._hold += delta_time
            can_step = (
                self._move_from is None and self.active_battle is None
                and self.manager.current is self and self._hold >= HOLD_DELAY
            )
            if can_step:
                self._try_move(*held)
        if self._portal_sprite is not None and self._portal_frames:
            idx = int(self._anim / PORTAL_FRAME_TIME) % len(self._portal_frames)
            self._portal_sprite.texture = self._portal_frames[idx]

    def draw(self):
        if self.camera is not None:
            self.camera.position = self._player_sprite.position
            self.camera.use()
        self.tiles.draw(pixelated=True)
        self.features.draw(pixelated=True)
        self._draw_monsters()
        self.player.draw(pixelated=True)
        self.app.default_camera.use()
        if self.hud is not None:
            self.hud.draw(self.run, extra=f"Steps {self.run.steps_since_encounter}   [M] map")
        if self.minimap is not None:
            self.minimap.draw(self.pos, self._visible_monsters())
        if self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, self.app.width, self.app.height, (0, 0, 0, 150))
            cx, cy = self.app.width / 2, self.app.height / 2
            frame.draw_window(cx - 340, cy - fs(215), 680, fs(215) + 110)
            self._pause_title.draw()
            self._pause_view.draw()
            self._pause_legend.draw()

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
