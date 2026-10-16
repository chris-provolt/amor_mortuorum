"""Turn-based combat scene: command menu, target cycling, log, HP panels."""
from __future__ import annotations

import logging
import math
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

import arcade

from ..core.scenes.base_scene import BaseScene
from ..errors import AmorError
from ..systems.combat import Action, ActionKind, Battle, LogEvent, Outcome
from ..systems.party import most_wounded
from ..ui import frame, pixelart, tiles
from ..ui.menu import MenuItem, MenuView, VerticalMenu
from ..ui.theme import fs

Color = arcade.types.Color
WALL_TOP_TINT = Color(110, 110, 130, 255)
WALL_FACE_TINT = Color(150, 150, 170, 255)

logger = logging.getLogger(__name__)

TEXT = (230, 230, 240)
DIM = (150, 150, 165)
HP_FRONT = (190, 60, 60)
HP_PARTY = (70, 170, 110)
TARGET = (255, 215, 120)
FLASH = (200, 40, 40)
STAGE_TILE = 64         # px: backdrop tile size on screen
ENEMY_SCALE = 4.0       # 32 px art drawn at 128 px on the stage
PARTY_SCALE = 3.0
IDLE_FRAME_TIME = 0.5
HIT_SHAKE_TIME = 0.3    # seconds a struck battler shudders
LUNGE_PX = 44           # how far an attacker lunges towards its target
IMPACT_AT = 0.45        # share of a strike's duration before the blow lands
DEATH_TIME = 0.55       # seconds a fallen foe takes to dissolve
NUMBER_TIME = 0.8       # seconds a damage number floats
# Seconds each log event takes to play on the battle screen
EVENT_TIME = {
    "round": 0.3, "slash": 0.7, "spell": 0.75, "cast": 0.45, "heal": 0.65,
    "item": 0.6, "guard": 0.4, "death": DEATH_TIME, "rage": 0.45, "flee": 0.6,
    "flee_fail": 0.45, "victory": 0.35, "defeat": 0.35, "miss": 0.35, "none": 0.35,
}
FX_SPELL = (190, 120, 255)
FX_HEAL = (120, 240, 150)
FX_ITEM = (255, 220, 120)
FX_RAGE = (255, 90, 70)
FX_SLASH = (255, 255, 255)
NUM_DAMAGE = (255, 240, 230)
NUM_PARTY = (255, 110, 110)
NUM_HEAL = (150, 255, 170)
MP_FRONT = (90, 120, 220)
FLASH_TIME = 0.35   # seconds the hit flash takes to fade
FLASH_ALPHA = 120   # peak alpha of the flash overlay


def lunge_offset(progress: float, reach: float = LUNGE_PX) -> float:
    """Distance an attacker has lunged ``progress`` (0..1) into a strike: a quick
    dash in, the blow at the apex, and a slower return."""
    p = max(0.0, min(1.0, progress))
    if p < IMPACT_AT:
        return reach * math.sin(math.pi / 2 * p / IMPACT_AT)
    return reach * math.cos(math.pi / 2 * (p - IMPACT_AT) / (1 - IMPACT_AT))


def flash_alpha(remaining: float, total: float = FLASH_TIME, peak: int = FLASH_ALPHA) -> int:
    """Overlay alpha for a flash with ``remaining`` seconds left: linear fade to zero."""
    if total <= 0 or remaining <= 0:
        return 0
    return int(round(peak * min(1.0, remaining / total)))


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
    def __init__(self, app, battle: Battle, title: Optional[str] = None):
        super().__init__(app)
        self.battle = battle
        self.title = title
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
        self._flash = 0.0  # seconds of hit flash left
        self._anim = 0.0
        self._hits: Dict[Tuple[str, int], float] = {}  # (side, index) -> shake time left
        self._flipped: Dict[Tuple[str, int], arcade.Texture] = {}
        # Animation queue: log events play one at a time
        self._queue: Deque[LogEvent] = deque()
        self._current: Optional[LogEvent] = None
        self._cur_t = 0.0
        self._cur_dur = 0.0
        self._impact_done = False
        self._fx: List[dict] = []            # transient effects (slash, burst, glyph)
        self._numbers: List[dict] = []       # floating damage/heal numbers
        self._dying: Dict[Tuple[str, int], float] = {}  # (side, idx) -> fade progress
        self._layout: Dict[str, Tuple[float, float, float, float]] = {}

    # Lifecycle

    def on_enter(self):
        super().on_enter()
        names = ", ".join(e.name for e in self.battle.enemies)
        self._header = arcade.Text(
            self.title or f"Ambush! {names}", 0, 0, color=TARGET, font_size=fs(18),
            anchor_x="center", anchor_y="top",
        )
        self._prompt = arcade.Text("", 0, 0, color=DIM, font_size=fs(12), anchor_x="center")
        self._log_rows = [arcade.Text("", 0, 0, font_size=fs(13), anchor_y="top") for _ in range(7)]
        self._enemy_rows = [
            arcade.Text("", 0, 0, color=TEXT, font_size=fs(15), anchor_y="center")
            for _ in self.battle.enemies
        ]
        self._party_rows = [
            arcade.Text("", 0, 0, color=TEXT, font_size=fs(15), anchor_y="center")
            for _ in self.battle.party
        ]
        self._view = MenuView(self.menu, 0, 0, font_size=fs(18))
        self.menu.sfx = self.app.audio.play
        self.app.audio.play_music("combat")
        self._log.append(LogEvent("The dead stir.", "info"))
        self._pick_next_actor()
        self._show_command_menu()
        self.on_resize(self.app.width, self.app.height)

    def on_resize(self, width: int, height: int):
        """Stage on top, three windows along the bottom: foes, commands, party."""
        pad = 8
        panel_h = max(fs(196), height * 0.36)
        stage_bottom = panel_h + pad
        col = (width - pad * 4) / 10
        foes = (pad, pad, col * 3.6, panel_h)
        cmds = (foes[0] + foes[2] + pad, pad, col * 2.2, panel_h)
        party = (cmds[0] + cmds[2] + pad, pad, width - cmds[0] - cmds[2] - pad * 2, panel_h)
        log_h = fs(20) * 4 + 14
        log = (pad, height - pad - log_h, width * 0.5, log_h)
        self._layout = {
            "foes": foes, "cmds": cmds, "party": party, "log": log,
            "stage": (0, stage_bottom, width, height - stage_bottom),
        }
        if self._header is not None:
            self._header.position = (width * 0.75, height - pad - 6)
        if self._prompt is not None:
            self._prompt.position = (width * 0.75, height - pad - fs(54))
        row_step = fs(40)
        for i, row in enumerate(self._enemy_rows):
            row.position = (foes[0] + 16, foes[1] + foes[3] - 26 - i * row_step)
        for i, row in enumerate(self._party_rows):
            row.position = (party[0] + 16, party[1] + party[3] - 26 - i * row_step)
        for i, row in enumerate(self._log_rows[:4]):
            row.position = (log[0] + 12, log[1] + log[3] - 8 - i * fs(20))
        if self._view is not None:
            self._view.set_position(cmds[0] + 18, cmds[1] + cmds[3] - 36)

    # Stage positions

    def _enemy_spot(self, i: int, count: int) -> Tuple[float, float]:
        """Foes stand on the left half of the stage, staggered in depth."""
        sl, sb, sw, sh = self._layout["stage"]
        span = sw * 0.42
        x = sl + sw * 0.08 + (span / max(1, count)) * (i + 0.5)
        y = sb + sh * 0.30 + (i % 2) * sh * 0.12
        return x, y

    def _party_spot(self, i: int, count: int) -> Tuple[float, float]:
        """The party lines up on the right, facing the foes."""
        sl, sb, sw, sh = self._layout["stage"]
        x = sl + sw * 0.78 + (i % 2) * sw * 0.07
        step = min(sh * 0.22, (sh * 0.75) / max(1, count))
        y = sb + sh * 0.66 - i * step
        return x, y

    # Menus

    def _show_command_menu(self) -> None:
        self.mode = "command"
        self.menu.set_items(
            [
                MenuItem("Attack", self._attack, hint="Left/Right to change target"),
                MenuItem("Skill", self._show_skill_menu, hint="Spend MP on a spell"),
                MenuItem("Item", self._show_item_menu, hint="Use a potion or scroll"),
                MenuItem("Defend", self._defend, hint="Halve damage this round"),
                MenuItem("Flee", self._flee, hint="Chance depends on speed"),
            ],
            keep_selection=False,
        )

    def _show_skill_menu(self) -> None:
        player = self.battle.party[self.actor]
        items: List[MenuItem] = []
        for skill in player.known_skills(self.data):
            if skill.heal:
                effect = f"Heals {skill.heal}"
            elif skill.target == "all_enemies":
                effect = f"{skill.damage}+ to every foe"
            else:
                effect = f"{skill.damage}+ damage"
            can = player.stats.mp >= skill.mp
            items.append(
                MenuItem(
                    f"{skill.name:<14} {skill.mp:>3} MP",
                    lambda sid=skill.id: self._use_skill(sid),
                    enabled=can,
                    hint=effect if can else f"Not enough MP ({effect})",
                )
            )
        if not items:
            self._log.append(LogEvent("No skills learned yet.", "info"))
            return
        items.append(MenuItem("Back", self._show_command_menu))
        self.mode = "skill"
        self.menu.set_items(items, keep_selection=False)

    def _ally_target(self) -> int:
        wounded = most_wounded(self.battle.party)
        return self.actor if wounded is None else wounded

    def _use_skill(self, skill_id: str) -> None:
        skill = self.data.skill(skill_id)
        target = self._ally_target() if skill.target == "ally" else self.target
        self._submit(Action(ActionKind.SKILL, self.actor, target=target, skill_id=skill_id))

    def _show_item_menu(self) -> None:
        items: List[MenuItem] = []
        for item_id, qty in sorted(self.battle.bag.items.items()):
            item = self.data.item(item_id)
            if not item.usable_in_combat:
                continue
            if item.hp_restore:
                effect = f"Heals {item.hp_restore}"
            elif item.mp_restore:
                effect = f"Restores {item.mp_restore} MP"
            else:
                effect = f"Deals {item.damage}"
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
        if events:
            # The round resolved: play it out before anyone acts again
            self._queue.extend(events)
            self.mode = "anim"
            self.menu.set_items([], keep_selection=False)
            return
        self._pick_next_actor()
        self._refresh_target()
        self._show_command_menu()

    # Animation queue

    def _spot(self, side: Tuple[str, int]) -> Tuple[float, float]:
        kind, idx = side
        if kind == "foe":
            return self._enemy_spot(idx, len(self.battle.foes))
        return self._party_spot(idx, len(self.battle.players))

    def _add_fx(self, kind: str, side: Tuple[str, int], color, dur: float = 0.45) -> None:
        x, y = self._spot(side)
        self._fx.append({"kind": kind, "x": x, "y": y, "t": 0.0, "dur": dur, "color": color})

    def _add_number(self, side: Tuple[str, int], text: str, color) -> None:
        x, y = self._spot(side)
        label = arcade.Text(text, x, y + 30, color=color, font_size=fs(20), bold=True,
                            anchor_x="center", anchor_y="center")
        self._numbers.append({"text": label, "y": y + 30, "t": 0.0})

    def _start_event(self, ev: LogEvent) -> None:
        """Begin playing one log event: show its line and set up its visuals."""
        self._current = ev
        self._cur_t = 0.0
        self._cur_dur = EVENT_TIME.get(ev.effect, EVENT_TIME["none"])
        self._impact_done = False
        self._log.append(ev)
        audio = self.app.audio
        if ev.effect == "cast" and ev.actor is not None:
            self._add_fx("burst", ev.actor, FX_SPELL, 0.45)
        elif ev.effect == "heal":
            audio.play("heal")
            if ev.target is not None:
                self._add_fx("heal", ev.target, FX_HEAL, 0.6)
                self._add_number(ev.target, f"+{ev.amount}", NUM_HEAL)
        elif ev.effect == "guard" and ev.actor is not None:
            self._add_fx("guard", ev.actor, FX_ITEM, 0.4)
        elif ev.effect == "death" and ev.target is not None:
            self._dying[ev.target] = 0.0
        elif ev.effect == "rage" and ev.target is not None:
            self._add_fx("burst", ev.target, FX_RAGE, 0.45)
            self._hits[ev.target] = HIT_SHAKE_TIME
        elif ev.effect == "flee":
            audio.play("flee")
        elif ev.effect == "victory":
            audio.play("victory")
        elif ev.effect == "defeat":
            audio.play("defeat")

    def _impact(self, ev: LogEvent) -> None:
        """The blow lands: shake and flash the target, show the number and effect."""
        self._impact_done = True
        if ev.target is None:
            return
        self._hits[ev.target] = HIT_SHAKE_TIME
        if ev.target[0] == "party":
            self._flash = FLASH_TIME
        self.app.audio.play("hit")
        color = NUM_PARTY if ev.target[0] == "party" else NUM_DAMAGE
        self._add_number(ev.target, str(ev.amount), color)
        if ev.effect == "slash":
            self._add_fx("slash", ev.target, FX_SLASH, 0.3)
        else:
            self._add_fx("burst", ev.target, FX_SPELL if ev.kind == "item" else FX_ITEM, 0.5)

    def _finish_queue(self) -> None:
        if self.battle.outcome is not Outcome.ONGOING:
            self.mode = "done"
            self.menu.set_items([], keep_selection=False)
            return
        self._pick_next_actor()
        self._refresh_target()
        self._show_command_menu()

    def _advance_queue(self, delta_time: float) -> None:
        if self._current is None:
            if not self._queue:
                if self.mode == "anim":
                    self._finish_queue()
                return
            self._start_event(self._queue.popleft())
        ev = self._current
        self._cur_t += delta_time
        if (ev.effect in ("slash", "spell") and not self._impact_done
                and self._cur_t >= self._cur_dur * IMPACT_AT):
            self._impact(ev)
        if self._cur_t >= self._cur_dur:
            if ev.effect in ("slash", "spell") and not self._impact_done:
                self._impact(ev)
            self._current = None

    def skip_animation(self) -> None:
        """Fast-forward the event being played (confirm during a round)."""
        if self._current is not None:
            self._cur_t = self._cur_dur

    def _lunge(self, side: Tuple[str, int]) -> float:
        """Horizontal offset of a battler mid-strike (foes lunge right, the party left)."""
        ev = self._current
        if ev is None or ev.effect != "slash" or ev.actor != side or self._cur_dur <= 0:
            return 0.0
        direction = 1.0 if side[0] == "foe" else -1.0
        return direction * lunge_offset(self._cur_t / self._cur_dur)

    def _attack(self) -> None:
        self._refresh_target()
        self._submit(Action(ActionKind.ATTACK, self.actor, target=self.target))

    def _defend(self) -> None:
        self._submit(Action(ActionKind.DEFEND, self.actor))

    def _flee(self) -> None:
        self._submit(Action(ActionKind.FLEE, self.actor))

    def _use_item(self, item_id: str) -> None:
        item = self.data.item(item_id)
        target = self.target if item.damage > 0 else self._ally_target()
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

    def update(self, delta_time: float):
        if self._flash > 0:
            self._flash = max(0.0, self._flash - delta_time)
        self._anim += delta_time
        for key in list(self._hits):
            self._hits[key] -= delta_time
            if self._hits[key] <= 0:
                del self._hits[key]
        if self.mode == "anim":
            self._advance_queue(delta_time)
        for fx in self._fx:
            fx["t"] += delta_time
        self._fx = [fx for fx in self._fx if fx["t"] < fx["dur"]]
        for num in self._numbers:
            num["t"] += delta_time
        self._numbers = [n for n in self._numbers if n["t"] < NUMBER_TIME]
        for key in list(self._dying):
            self._dying[key] = min(1.0, self._dying[key] + delta_time / DEATH_TIME)

    def _shake(self, key: Tuple[str, int]) -> float:
        left = self._hits.get(key, 0.0)
        return math.sin(self._anim * 70) * 6 * (left / HIT_SHAKE_TIME) if left > 0 else 0.0

    def _party_texture(self, art: str, frame: int, i: int) -> arcade.Texture:
        """Party sprites face left towards the foes; flipped textures are cached."""
        key = (f"{art}:{frame}", i)
        tex = self._flipped.get(key)
        if tex is None:
            tex = pixelart.texture(art, frame).flip_left_right()
            self._flipped[key] = tex
        return tex

    def _draw_stage(self) -> None:
        """A dungeon backdrop: wall top, brick face, then floor receding into shadow."""
        sl, sb, sw, sh = self._layout["stage"]
        top = sb + sh
        wall_top = tiles.wall_texture("rooms", False, (False, False, False, False))
        wall_face = tiles.wall_texture("rooms", True, (False, False, False, False), 1)
        cols = int(sw // STAGE_TILE) + 2
        y = top - STAGE_TILE * 0.6
        for c in range(cols):
            rect = arcade.LBWH(sl + c * STAGE_TILE, y, STAGE_TILE, STAGE_TILE)
            arcade.draw_texture_rect(wall_top, rect, pixelated=True, color=WALL_TOP_TINT)
        y -= STAGE_TILE
        for c in range(cols):
            rect = arcade.LBWH(sl + c * STAGE_TILE, y, STAGE_TILE, STAGE_TILE)
            arcade.draw_texture_rect(wall_face, rect, pixelated=True, color=WALL_FACE_TINT)
        floor_top = y
        rows = int((floor_top - sb) // STAGE_TILE) + 1
        for r in range(rows):
            yy = floor_top - (r + 1) * STAGE_TILE
            depth = 1 - r / max(1, rows)  # back rows (r = 0) are darkest
            tone = int(90 + 150 * (1 - depth))
            for c in range(cols):
                tex = tiles.floor_texture("rooms", c, r, r == 0, False, decals=False)
                rect = arcade.LBWH(sl + c * STAGE_TILE, yy, STAGE_TILE, STAGE_TILE)
                arcade.draw_texture_rect(
                    tex, rect, pixelated=True, color=Color(tone, tone, min(255, tone + 12), 255)
                )
        # Soft shadow where the stage meets the windows
        arcade.draw_lbwh_rectangle_filled(sl, sb, sw, 10, (0, 0, 0, 90))

    def _draw_battlers(self) -> None:
        frame = int(self._anim / IDLE_FRAME_TIME) % 2
        foes = self.battle.foes
        for i, b in enumerate(foes):
            dying = self._dying.get(("foe", i))
            if not b.is_alive and (dying is None or dying >= 1.0):
                continue
            x, y = self._enemy_spot(i, len(foes))
            x += self._shake(("foe", i)) + self._lunge(("foe", i))
            size = pixelart.RENDER_PX * ENEMY_SCALE
            alpha = 255
            if dying is not None and dying < 1.0:
                alpha = int(255 * (1 - dying))
                size *= 1 - 0.3 * dying
            arcade.draw_ellipse_filled(
                x, y - size * 0.46, size * 0.7, size * 0.16, (0, 0, 0, 90 * alpha // 255)
            )
            tex = pixelart.texture(pixelart.enemy_sprite_name(b.ref.def_id), frame)
            rect = arcade.LBWH(x - size / 2, y - size / 2, size, size)
            if dying is not None and dying < 1.0:
                arcade.draw_texture_rect(
                    tex, rect, pixelated=True, alpha=alpha, color=Color(255, 120, 120, 255)
                )
            else:
                arcade.draw_texture_rect(tex, rect, pixelated=True)
            if b.index == self.target and self.mode not in ("done", "anim") and b.is_alive:
                bob = math.sin(self._anim * 6) * 4
                ty = y + size / 2 + 10 + bob
                arcade.draw_polygon_filled(
                    [(x - 9, ty + 14), (x + 9, ty + 14), (x, ty)], TARGET
                )
        players = self.battle.players
        for i, b in enumerate(players):
            x, y = self._party_spot(i, len(players))
            x += self._shake(("party", i)) + self._lunge(("party", i))
            size = pixelart.RENDER_PX * PARTY_SCALE
            art = pixelart.party_sprite_name(getattr(b.ref, "companion_id", None))
            alive = b.is_alive
            arcade.draw_ellipse_filled(x, y - size * 0.46, size * 0.7, size * 0.16, (0, 0, 0, 90))
            tex = self._party_texture(art, frame if alive else 0, i)
            rect = arcade.LBWH(x - size / 2, y - size / 2, size, size)
            if alive:
                arcade.draw_texture_rect(tex, rect, pixelated=True)
            else:  # fallen: laid flat and dimmed
                arcade.draw_texture_rect(
                    tex, rect, pixelated=True, angle=90, color=Color(120, 120, 140, 255), alpha=180
                )
            if b.index == self.actor and self.mode not in ("done", "anim") and alive:
                bob = math.sin(self._anim * 6) * 4
                ty = y + size / 2 + 8 + bob
                arcade.draw_polygon_filled(
                    [(x - 8, ty + 12), (x + 8, ty + 12), (x, ty)], (200, 230, 255)
                )

    def _draw_effects(self) -> None:
        """Slashes, bursts, heal sparkles, guard glyphs and floating numbers."""
        for fx in self._fx:
            p = fx["t"] / fx["dur"]
            x, y = fx["x"], fx["y"]
            a = int(255 * (1 - p))
            color = (*fx["color"], a)
            if fx["kind"] == "slash":
                for k in range(3):
                    off = (k - 1) * 14
                    sweep = p * 70
                    arcade.draw_line(
                        x - 40 + sweep + off, y + 40 - off, x - 10 + sweep + off, y - 30 - off,
                        color, 4 - k,
                    )
            elif fx["kind"] == "burst":
                r = 12 + 60 * p
                arcade.draw_circle_outline(x, y, r, color, 3)
                arcade.draw_circle_outline(x, y, r * 0.6, color, 2)
                for k in range(6):
                    ang = k * math.pi / 3 + p * 2
                    arcade.draw_circle_filled(
                        x + math.cos(ang) * r, y + math.sin(ang) * r, 3, color
                    )
            elif fx["kind"] == "heal":
                for k in range(7):
                    ang = k * 0.9
                    sx = x + math.cos(ang) * 28
                    sy = y - 30 + (p * 80 + k * 9) % 80
                    arcade.draw_circle_filled(sx, sy, 3, color)
                    arcade.draw_line(sx - 5, sy, sx + 5, sy, color, 1)
                    arcade.draw_line(sx, sy - 5, sx, sy + 5, color, 1)
            elif fx["kind"] == "guard":
                top = y + 56 + 6 * math.sin(p * math.pi)
                shield = [(x - 14, top), (x + 14, top), (x + 14, top - 16),
                          (x, top - 30), (x - 14, top - 16)]
                arcade.draw_polygon_filled(shield, (60, 80, 160, a))
                arcade.draw_polygon_outline(shield, color, 2)
        for num in self._numbers:
            p = num["t"] / NUMBER_TIME
            label = num["text"]
            label.y = num["y"] + 34 * p
            r, g, b = label.color[:3]
            label.color = (r, g, b, int(255 * (1 - p * p)))
            label.draw()

    def draw(self):
        w, h = self.app.width, self.app.height
        if not self._layout:
            self.on_resize(w, h)
        self._draw_stage()
        self._draw_battlers()
        self._draw_effects()
        alpha = flash_alpha(self._flash) if self.app.state.settings.video.screen_flash else 0
        if alpha > 0:
            arcade.draw_lbwh_rectangle_filled(0, 0, w, h, (*FLASH, alpha))

        foes_w = self._layout["foes"]
        frame.draw_window(*foes_w)
        bar_w = foes_w[2] - 48
        for row, b in zip(self._enemy_rows, self.battle.foes):
            text = f"{b.name}   {max(0, b.stats.hp)}/{b.stats.max_hp}"
            if row.text != text:
                row.text = text
            row.color = DIM if not b.is_alive else TARGET if b.index == self.target else TEXT
            row.draw()
            if b.index == self.target and b.is_alive and self.mode != "done":
                frame.draw_cursor(row.x - 12, row.y)
            frame.draw_gauge(
                row.x + 4, row.y - fs(18), bar_w, 7, b.stats.hp / b.stats.max_hp, HP_FRONT
            )

        party_w = self._layout["party"]
        frame.draw_window(*party_w)
        bar_w = (party_w[2] - 64) / 2
        for row, b in zip(self._party_rows, self.battle.players):
            text = f"{b.name}   HP {max(0, b.stats.hp)}/{b.stats.max_hp}  MP {b.stats.mp}"
            if b.defending:
                text += "  [guard]"
            if row.text != text:
                row.text = text
            row.color = DIM if not b.is_alive else TEXT
            row.draw()
            if b.index == self.actor and self.mode != "done" and b.is_alive:
                frame.draw_cursor(row.x - 12, row.y)
            frame.draw_gauge(
                row.x + 4, row.y - fs(18), bar_w, 7, b.stats.hp / b.stats.max_hp, HP_PARTY
            )
            frame.draw_gauge(
                row.x + 12 + bar_w, row.y - fs(18), bar_w, 7,
                b.stats.mp / b.stats.max_mp if b.stats.max_mp else 0.0, MP_FRONT,
            )

        frame.draw_window(*self._layout["log"], alpha=215)
        if self._header is not None:
            self._header.draw()
        for row, event in zip(self._log_rows[:4], list(self._log)[-4:][::-1]):
            if row.text != event.text:
                row.text = event.text
            row.color = LOG_COLORS.get(event.kind, DIM)
            row.draw()

        frame.draw_window(*self._layout["cmds"])

        if self.mode == "done":
            prompt = {
                Outcome.VICTORY: "Victory. Press Enter to continue.",
                Outcome.DEFEAT: "The party has fallen. Press Enter.",
                Outcome.FLED: "Escaped. Press Enter to continue.",
            }.get(self.battle.outcome, "")
        elif self.mode == "anim":
            prompt = "Enter skips"
        else:
            prompt = f"Round {self.battle.round_number}: choose an action"
        if self._prompt.text != prompt:
            self._prompt.text = prompt
        self._prompt.draw()
        if self._view is not None and self.mode not in ("done", "anim"):
            self._view.draw()

    # Input

    def on_key_actions(self, actions: list[str], pressed: bool) -> bool:
        if not pressed:
            return False
        if self.mode == "done":
            if "confirm" in actions:
                self._finish()
            return True
        if self.mode == "anim":
            if "confirm" in actions or "cancel" in actions:
                self.skip_animation()
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
            if self.mode in ("item", "skill"):
                self._show_command_menu()
            return True
        return False
