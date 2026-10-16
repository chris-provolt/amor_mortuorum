"""Scripted playthrough in a real window. Skipped unless AMOR_GL_TESTS=1.

Drives the scene stack with synthetic key presses and draws every step so
rendering errors surface. Run with:  AMOR_GL_TESTS=1 pytest -m gl
"""
from __future__ import annotations

import os
from collections import deque

import pytest

pytestmark = [
    pytest.mark.gl,
    pytest.mark.skipif(os.environ.get("AMOR_GL_TESTS") != "1", reason="needs a display"),
]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("AMOR_MUTE", "1")
    from amormortuorum.app import GameApp
    from amormortuorum.core.settings import Settings
    from amormortuorum.persistence import SaveManager

    settings = Settings.load()
    settings.video.width, settings.video.height = 960, 540
    game = GameApp(
        settings, save_manager=SaveManager(root_dir=tmp_path, profile_id="play"), seed=1
    )
    yield game
    game.close()


class Driver:
    def __init__(self, app):
        import arcade

        self.app = app
        self.keys = {
            "up": arcade.key.UP,
            "down": arcade.key.DOWN,
            "left": arcade.key.LEFT,
            "right": arcade.key.RIGHT,
            "enter": arcade.key.ENTER,
            "esc": arcade.key.ESCAPE,
            "tab": arcade.key.TAB,
            "m": arcade.key.M,
        }

    def frame(self, dt: float = 1 / 60):
        self.app.on_update(dt)
        self.app.on_draw()

    def press(self, name: str):
        key = self.keys[name]
        self.app.on_key_press(key, 0)
        self.app.on_key_release(key, 0)
        self.frame()

    @property
    def scene(self):
        return self.app.scene_manager.current

    def scene_name(self) -> str:
        return type(self.scene).__name__

    def boot_to_menu(self):
        self.frame(1.2)
        assert self.scene_name() == "MainMenuScene"

    def settle(self, limit: int = 200):
        """Let a combat round's animations finish."""
        for _ in range(limit):
            if getattr(self.scene, "mode", "") != "anim":
                return
            self.frame(0.25)

    def fight_until_done(self, max_steps: int = 600, *, max_rounds: int = 0):
        """Attack every round until the combat scene pops, letting rounds play out."""
        if max_rounds:
            max_steps = max(max_steps, max_rounds * 10)
        for _ in range(max_steps):
            if self.scene_name() != "CombatScene":
                return
            if getattr(self.scene, "mode", "") == "anim":
                self.frame(0.25)  # let the round's animations run
                continue
            self.press("enter")  # Attack (first menu item), or confirm on the result
        raise AssertionError("combat did not finish")


def _path(fmap, start, goal):
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        x, y = cur
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt not in prev and fmap.is_walkable(*nxt):
                prev[nxt] = cur
                queue.append(nxt)
    steps = []
    cur = goal
    while prev[cur] is not None:
        steps.append(cur)
        cur = prev[cur]
    return steps[::-1]


def _walk_to(driver: Driver, goal):
    scene = driver.scene
    path = _path(scene.fmap, scene.pos, goal)
    for nxt in path:
        # Walking into a wandering monster fights it without moving, so a tile may
        # take a few presses before the party stands on it.
        for _ in range(6):
            if driver.scene_name() == "CombatScene":
                driver.fight_until_done()
            if driver.scene_name() != "DungeonScene":
                return  # died (summary) or left the floor
            scene = driver.scene
            if scene.pos == nxt:
                break
            dx, dy = nxt[0] - scene.pos[0], nxt[1] - scene.pos[1]
            key = {(1, 0): "right", (-1, 0): "left", (0, 1): "up", (0, -1): "down"}[(dx, dy)]
            driver.press(key)
    if driver.scene_name() == "CombatScene":  # an encounter on the final step
        driver.fight_until_done()


def test_full_loop_menu_graveyard_dungeon_combat_stairs(app):
    d = Driver(app)
    d.boot_to_menu()

    d.press("enter")  # New Run
    assert d.scene_name() == "GraveyardScene"
    run = app.state.run
    assert run.floor == 1 and run.in_graveyard

    # Rest, open and close the crypt, then enter the dungeon
    d.press("down")
    d.press("enter")  # Rest
    d.press("down")
    d.press("enter")  # Crypt submenu
    d.press("esc")  # back (cursor resets to the first item)
    assert d.scene.mode == "main"
    d.press("enter")  # Enter the Dungeon
    assert d.scene_name() == "DungeonScene"
    assert run.in_graveyard is False

    dungeon = d.scene
    # Walls block movement: try every direction from the start and confirm we stay on floor tiles
    for key in ("up", "down", "left", "right"):
        d.press(key)
        assert dungeon.fmap.is_walkable(*d.scene.pos)

    # Walk the reachable chests, then the stairs; fight whatever shows up
    for chest in sorted(dungeon.fmap.chests):
        if d.scene_name() != "DungeonScene":
            break
        _walk_to(d, chest)
    if d.scene_name() == "DungeonScene":
        _walk_to(d, dungeon.fmap.stairs)
    if d.scene_name() == "CombatScene":
        d.fight_until_done()

    if d.scene_name() == "DungeonScene":
        assert d.scene.pos == dungeon.fmap.stairs
        d.press("enter")  # descend
        assert d.scene_name() == "DungeonScene"
        assert run.floor == 2
        assert d.scene.fmap.floor == 2
    else:
        # Party wiped on floor 1 with the token: we are at the summary, then the Graveyard
        assert d.scene_name() == "RunSummaryScene"
        d.press("enter")
        assert d.scene_name() == "GraveyardScene"

    # Pause menu opens and closes on the dungeon
    if d.scene_name() == "DungeonScene":
        d.press("esc")
        assert d.scene.paused
        d.frame()  # overlay, menu and marker legend draw
        d.press("esc")
        assert not d.scene.paused


def test_death_with_token_returns_to_graveyard_and_consumes_it(app):
    from amormortuorum.systems.combat import Battle, Outcome
    from amormortuorum.systems.entities import Enemy
    from amormortuorum.scenes.combat import CombatScene
    from amormortuorum.systems.rng import stream_rng

    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    assert d.scene_name() == "DungeonScene"
    run = app.state.run
    data = app.state.data
    assert run.has_token()

    # Force a hopeless fight: 1 HP against a titan
    run.leader.stats.hp = 1
    titan = Enemy.from_def(data.enemy("grave_titan"))
    battle = Battle(run.party, [titan], stream_rng(1, 1, "test"), data)
    d.scene.active_battle = battle
    app.scene_manager.push(CombatScene(app, battle))
    d.frame()
    d.fight_until_done()
    assert battle.outcome is Outcome.DEFEAT

    assert d.scene_name() == "RunSummaryScene"
    assert run.has_token() is False
    assert run.leader.hp == 1
    d.press("enter")
    assert d.scene_name() == "GraveyardScene"
    assert run.in_graveyard is True


def test_death_without_token_ends_run_and_clears_save(app):
    from amormortuorum.systems.combat import Battle
    from amormortuorum.systems.entities import Enemy
    from amormortuorum.systems.hub import GraveyardHub
    from amormortuorum.scenes.combat import CombatScene
    from amormortuorum.systems.rng import stream_rng
    from amormortuorum.systems.run import RESURRECTION_TOKEN_ID

    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    run = app.state.run
    data = app.state.data
    run.leader.inventory.remove(data.item(RESURRECTION_TOKEN_ID), 1)
    run.leader.stats.hp = 1

    titan = Enemy.from_def(data.enemy("grave_titan"))
    battle = Battle(run.party, [titan], stream_rng(2, 1, "t"), data)
    d.scene.active_battle = battle
    app.scene_manager.push(CombatScene(app, battle))
    d.frame()
    d.fight_until_done()

    assert d.scene_name() == "RunSummaryScene"
    d.press("enter")
    assert d.scene_name() == "MainMenuScene"
    assert app.state.run is None
    hub = GraveyardHub(app.state.save_manager, data, meta=app.state.meta)
    assert hub.load_run() is None
    assert app.state.meta.runs_completed == 1
    # Continue is disabled; New Run still works
    assert d.scene.menu.items[1].enabled is False


def test_shop_and_inventory_screens(app):
    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    assert d.scene_name() == "GraveyardScene"
    run = app.state.run
    data = app.state.data
    leader = run.leader
    gold_before = leader.gold

    # Shop: buy the first affordable item once
    d.press("down")
    d.press("down")
    d.press("enter")  # Shop (Enter, Rest, Shop, ...)
    assert d.scene.mode == "shop"
    stock = d.scene.ctx.shop.stock()
    first_id = sorted(stock)[0]
    assert leader.gold >= stock[first_id].price, "seeded stock should be affordable"
    bag_before = leader.inventory.count(first_id)
    d.press("enter")  # buy one
    assert leader.gold == gold_before - stock[first_id].price
    assert leader.inventory.count(first_id) == bag_before + 1
    d.press("esc")
    assert d.scene.mode == "main"

    # Inventory: equip a blade from the bag via Tab, then unequip it
    leader.inventory.add(data.item("blade_bone"), 1)
    base_atk = leader.effective_atk(data)
    d.press("tab")
    assert d.scene_name() == "InventoryScene"
    labels = [it.label for it in d.scene.menu.items]
    idx = next(i for i, label in enumerate(labels) if "Bone Shard Blade" in label)
    for _ in range(idx - d.scene.menu.selected):
        d.press("down")
    d.press("enter")  # equip
    assert leader.equipment.slots["weapon"] == "blade_bone"
    assert leader.effective_atk(data) == base_atk + 3
    while d.scene.menu.selected != 0:
        d.press("up")
    d.press("enter")  # unequip weapon slot
    assert leader.equipment.slots["weapon"] is None
    assert leader.inventory.count("blade_bone") == 1
    d.press("esc")
    assert d.scene_name() == "GraveyardScene"

    # Level-up after a victory in the dungeon is reflected in the HUD and stats
    d.press("enter")  # Enter the Dungeon (cursor reset to first item)
    assert d.scene_name() == "DungeonScene"
    from amormortuorum.systems.combat import Battle
    from amormortuorum.systems.entities import Enemy
    from amormortuorum.scenes.combat import CombatScene
    from amormortuorum.systems.rng import stream_rng

    leader.xp = data.xp_curve.xp_for_level(2) - 1
    weak = Enemy.from_def(data.enemy("skel_basic"))
    weak.stats.hp = 1
    battle = Battle(run.party, [weak], stream_rng(3, 1, "t"), data)
    d.scene.active_battle = battle
    app.scene_manager.push(CombatScene(app, battle))
    d.frame()
    d.fight_until_done()
    assert d.scene_name() == "DungeonScene"
    assert leader.level == 2
    assert any("Level 2!" in m for m in d.scene.hud.messages)


def test_locked_floor_key_door_and_trap(app):
    from amormortuorum.systems.procgen import KEY_ITEM_ID, generate_floor

    # Pick a floor-5 seed whose stairs room is locked and that carries a trap
    seed = next(
        s for s in range(1, 200) if generate_floor(s, 5).doors and generate_floor(s, 5).traps
    )
    app.state.seed = seed
    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    run = app.state.run
    run.floor = 5
    run.leader.stats.max_hp = run.leader.stats.hp = 500  # survive whatever floor 5 throws
    run.leader.stats.atk = 60
    d.press("enter")  # Enter the Dungeon
    assert d.scene_name() == "DungeonScene"
    scene = d.scene
    fmap = scene.fmap
    assert fmap.doors and fmap.keys and fmap.traps
    assert fmap.floor == 5 and fmap.seed == seed

    # The door blocks until we hold a key
    door = next(iter(fmap.doors))
    assert not run.leader.inventory.has(KEY_ITEM_ID)

    # Walk to a trap first: it reveals, deals damage, and is spent
    trap_pos = next(iter(fmap.traps))
    hp_before = run.leader.hp
    _walk_to(d, trap_pos)
    if d.scene_name() == "DungeonScene" and d.scene.pos == trap_pos:
        assert fmap.traps[trap_pos].revealed and not fmap.traps[trap_pos].armed
        assert run.leader.hp < hp_before or run.leader.hp == run.leader.max_hp
        assert fmap.feature_at(*trap_pos) == "trap"

    # Pick up the key
    key_pos = next(iter(fmap.keys))
    _walk_to(d, key_pos)
    assert d.scene_name() == "DungeonScene"
    assert run.leader.inventory.has(KEY_ITEM_ID)
    assert not fmap.keys

    # Step into a door from a reachable neighbour: it unlocks and consumes the key
    from amormortuorum.systems.procgen import bfs_reachable

    outside = bfs_reachable(fmap, d.scene.pos)
    door, approach = next(
        (dr, n)
        for dr in fmap.doors
        for n in ((dr[0] + 1, dr[1]), (dr[0] - 1, dr[1]), (dr[0], dr[1] + 1), (dr[0], dr[1] - 1))
        if n in outside
    )
    _walk_to(d, approach)
    assert d.scene.pos == approach
    step = {(1, 0): "right", (-1, 0): "left", (0, 1): "up", (0, -1): "down"}[
        (door[0] - approach[0], door[1] - approach[1])
    ]
    d.press(step)
    assert fmap.is_walkable(*door)
    assert not run.leader.inventory.has(KEY_ITEM_ID)
    assert any("key turns" in m for m in d.scene.hud.messages)

    # Now the stairs are reachable; descend
    _walk_to(d, fmap.stairs)
    assert d.scene_name() == "DungeonScene" and d.scene.pos == fmap.stairs
    d.press("enter")
    assert run.floor == 6


def test_fog_of_war_and_minimap(app):
    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    scene = d.scene
    assert scene.pos in scene.vis.visible
    explored_before = set(scene.vis.explored)
    assert explored_before, "the start area is explored on entry"
    # Tiles outside sight are invisible; the start tile is fully lit
    assert scene._tile_sprites[scene.pos].alpha == 255
    unseen = next(p for p in scene._tile_sprites if p not in scene.vis.explored)
    assert scene._tile_sprites[unseen].alpha == 0

    # Walk towards the stairs for a few steps; explored area grows
    _walk_to(d, scene.fmap.stairs)
    if d.scene_name() == "DungeonScene":
        assert d.scene.vis.explored > explored_before
        start_state = d.scene.vis.state(scene.fmap.start)
        assert start_state in ("visible", "explored")

    # Minimap toggles with M and draws without error in both states
    if d.scene_name() == "DungeonScene":
        assert d.scene.minimap.enabled
        d.press("m")
        assert not d.scene.minimap.enabled
        d.press("m")
        assert d.scene.minimap.enabled


def _enter_floor(d: Driver, app, floor: int, *, mighty: bool = True):
    d.boot_to_menu()
    d.press("enter")  # New Run
    run = app.state.run
    run.floor = floor
    if mighty:
        run.leader.stats.max_hp = run.leader.stats.hp = 5000
        run.leader.stats.atk = 400
    d.press("enter")  # Enter the Dungeon
    assert d.scene_name() == "DungeonScene"
    return run


def test_miniboss_gates_stairs_and_awards_relic(app):
    d = Driver(app)
    run = _enter_floor(d, app, 20)
    scene = d.scene
    assert scene.fmap.is_boss_floor and scene.fmap.stairs_locked
    assert not app.state.meta.relics.has("veil_3")

    _walk_to(d, scene.fmap.stairs)
    assert d.scene_name() == "DungeonScene" and d.scene.pos == scene.fmap.stairs
    d.press("enter")  # challenge the boss instead of descending
    assert d.scene_name() == "CombatScene"
    assert any(e.boss for e in d.scene.battle.enemies)
    d.fight_until_done()
    assert d.scene_name() == "DungeonScene"
    assert not scene.fmap.stairs_locked
    assert app.state.meta.relics.has("veil_3")
    assert any("Relic of the Veil" in m for m in scene.hud.messages)
    assert run.floor == 20
    d.press("enter")  # now the stairs work
    assert run.floor == 21

    # The relic persisted to disk
    assert app.state.save_manager.load_meta().relics.has("veil_3")


def test_final_boss_victory_ends_run(app):
    d = Driver(app)
    run = _enter_floor(d, app, 99)
    scene = d.scene
    _walk_to(d, scene.fmap.stairs)
    assert d.scene.pos == scene.fmap.stairs
    d.press("enter")
    assert d.scene_name() == "CombatScene"
    d.fight_until_done(max_rounds=200)
    assert d.scene_name() == "RunSummaryScene"
    assert d.scene.summary.victory and d.scene.summary.floor_reached == 99
    assert app.state.meta.relics.has("veil_final")
    d.press("enter")
    assert d.scene_name() == "MainMenuScene"
    assert app.state.run is None
    assert app.state.meta.runs_completed == 1 and app.state.meta.deepest_floor == 99
    assert d.scene.menu.items[1].enabled is False  # no run to continue
    del run


def test_relics_screen_and_chest_relic_pickup(app):
    d = Driver(app)
    d.boot_to_menu()
    # Relics screen from the title (Continue is disabled with no save, so one step down)
    d.press("down")
    assert d.scene.menu.current.label == "Relics"
    d.press("enter")
    assert d.scene_name() == "RelicsScene"
    d.press("esc")
    assert d.scene_name() == "MainMenuScene"
    while d.scene.menu.selected != 0:
        d.press("up")

    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    scene = d.scene
    run = app.state.run
    data = app.state.data
    # Force the next chest to yield a relic by pre-rolling the chest stream
    from amormortuorum.systems.loot import relic_chest_chance

    class AlwaysRelic:
        def __init__(self, inner):
            self.inner = inner

        def random(self):
            return 0.0  # below any relic chance

        def choice(self, seq):
            return self.inner.choice(seq)

        def randint(self, a, b):
            return self.inner.randint(a, b)

    assert relic_chest_chance(run.floor, data) > 0
    scene._chest_rng = AlwaysRelic(scene._chest_rng)
    before = set(app.state.meta.relics.collected)
    chest = sorted(scene.fmap.chests)[0]
    _walk_to(d, chest)
    if d.scene_name() == "DungeonScene" and d.scene.pos == chest:
        gained = set(app.state.meta.relics.collected) - before
        assert len(gained) == 1
        assert app.state.save_manager.load_meta().relics.collected >= gained
        assert any("Relic of the Veil" in m for m in d.scene.hud.messages)
        # Passives are live immediately
        from amormortuorum.systems.relics import passive_totals

        assert run.leader.bonuses == passive_totals(app.state.meta, data)


def test_save_and_quit_then_continue_mid_run(app):
    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    run = app.state.run
    run.floor = 3
    seed = run.seed
    d.scene.run.leader.take_damage(5)
    hp = run.leader.hp

    d.press("esc")  # pause
    labels = [it.label for it in d.scene.pause_menu.items]
    target = labels.index("Save & Quit")
    for _ in range(target - d.scene.pause_menu.selected):
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "MainMenuScene"
    assert app.state.run is None
    assert "mid-run" in d.scene.menu.items[1].hint

    d.press("down")  # Continue
    assert d.scene.menu.current.label == "Continue"
    d.press("enter")
    assert d.scene_name() == "DungeonScene"
    resumed = app.state.run
    assert resumed.floor == 3 and resumed.seed == seed and resumed.leader.hp == hp
    assert d.scene.fmap.floor == 3

    # The mid-run save was consumed: quitting again without saving loses it
    from amormortuorum.systems.hub import GraveyardHub

    hub = GraveyardHub(app.state.save_manager, app.state.data, meta=app.state.meta)
    assert hub.peek_run() is None


def test_skill_menu_casts_ember(app):
    from amormortuorum.systems.combat import Battle, Outcome
    from amormortuorum.systems.entities import Enemy
    from amormortuorum.scenes.combat import CombatScene
    from amormortuorum.systems.rng import stream_rng

    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    run = app.state.run
    data = app.state.data
    run.leader.stats.max_hp = run.leader.stats.hp = 500
    foe = Enemy.from_def(data.enemy("skel_basic"))
    battle = Battle(run.party, [foe], stream_rng(9, 1, "t"), data)
    d.scene.active_battle = battle
    app.scene_manager.push(CombatScene(app, battle))
    d.frame()

    mp = run.leader.stats.mp
    d.press("down")  # Skill
    assert d.scene.menu.current.label == "Skill"
    d.press("enter")
    assert d.scene.mode == "skill"
    assert "Ember" in d.scene.menu.current.label
    d.press("enter")  # cast
    d.settle()
    assert run.leader.stats.mp == mp - data.skill("ember").mp
    assert any("casts Ember" in e.text for e in d.scene._log)
    assert foe.stats.hp <= 0 or battle.outcome is Outcome.ONGOING
    d.fight_until_done()
    assert d.scene_name() == "DungeonScene"


def test_recruit_companion_and_switch_members_in_bag(app):
    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    run = app.state.run
    data = app.state.data
    run.leader.gold = 500

    # Graveyard: Enter, Rest, Shop, Crypt, Recruit, ...
    labels = [it.label for it in d.scene.menu.items]
    for _ in range(labels.index("Recruit")):
        d.press("down")
    d.press("enter")
    assert d.scene.mode == "recruit"
    d.press("enter")  # first companion (Ossian)
    assert len(run.party) == 2 and run.party[1].name == "Ossian"
    assert run.leader.gold == 500 - data.companion("ossian").cost
    d.press("esc")

    # Bag: Right switches to Ossian; equipping from the shared bag goes to him
    run.leader.inventory.add(data.item("blade_bone"), 1)
    d.press("tab")
    assert d.scene_name() == "InventoryScene" and d.scene.member == 0
    d.press("right")
    assert d.scene.member == 1
    labels = [it.label for it in d.scene.menu.items]
    idx = next(i for i, label in enumerate(labels) if "Bone Shard Blade" in label)
    for _ in range(idx - d.scene.menu.selected):
        d.press("down")
    d.press("enter")
    assert run.party[1].equipment.slots["weapon"] == "blade_bone"
    assert run.leader.equipment.slots["weapon"] is None
    d.press("esc")

    # Two-member party fights; both survivors gain XP
    d.press("enter")  # Enter the Dungeon (cursor reset)
    assert d.scene_name() == "DungeonScene"
    from amormortuorum.systems.combat import Battle
    from amormortuorum.systems.entities import Enemy
    from amormortuorum.scenes.combat import CombatScene
    from amormortuorum.systems.rng import stream_rng

    for m in run.party:
        m.stats.max_hp = m.stats.hp = 500
    xp0 = [m.xp for m in run.party]
    foe = Enemy.from_def(data.enemy("skel_basic"))
    battle = Battle(run.party, [foe], stream_rng(4, 1, "t"), data)
    d.scene.active_battle = battle
    app.scene_manager.push(CombatScene(app, battle))
    d.frame()
    d.fight_until_done()
    assert d.scene_name() == "DungeonScene"
    assert all(m.xp > x for m, x in zip(run.party, xp0))

    # Save/continue keeps the companion
    d.press("esc")
    labels = [it.label for it in d.scene.pause_menu.items]
    for _ in range(labels.index("Save & Quit") - d.scene.pause_menu.selected):
        d.press("down")
    d.press("enter")
    d.press("down")
    d.press("enter")  # Continue
    assert [m.name for m in app.state.run.party] == ["Wanderer", "Ossian"]


def test_settings_screen_adjusts_volume_and_saves(app, tmp_path, monkeypatch):
    from amormortuorum.core import settings as settings_mod
    from amormortuorum.scenes import settings as settings_scene

    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "user_settings_path", lambda: target)
    monkeypatch.setattr(settings_scene, "user_settings_path", lambda: target)

    d = Driver(app)
    d.boot_to_menu()
    while d.scene.menu.current.label != "Settings":
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "SettingsScene"

    d.press("down")  # Music volume
    assert d.scene.menu.current.payload == "music"
    before = app.settings.audio.music_volume
    d.press("left")
    assert app.settings.audio.music_volume == round(before - 0.1, 2)
    d.press("right")
    d.press("right")
    assert app.settings.audio.music_volume == round(before + 0.1, 2)

    while d.scene.menu.current.label != "Save":
        d.press("down")
    d.press("enter")
    assert target.exists()
    import json

    assert json.loads(target.read_text())["audio"]["music_volume"] == round(before + 0.1, 2)
    d.press("esc")
    assert d.scene_name() == "MainMenuScene"


def test_rebind_key_from_settings(app):
    import arcade

    d = Driver(app)
    d.boot_to_menu()
    while d.scene.menu.current.label != "Settings":
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "SettingsScene"
    while d.scene.menu.current.label != "Rebind keys":
        d.press("down")
    d.press("enter")
    assert d.scene.mode == "keys"
    while not d.scene.menu.current.label.startswith("map"):
        d.press("down")
    d.press("enter")
    assert d.scene.mode == "listen"
    app.on_key_press(arcade.key.N, 0)
    app.on_key_release(arcade.key.N, 0)
    d.frame()
    assert d.scene.mode == "keys"
    assert app.input.actions_for_key(arcade.key.N) == ["map"]
    assert app.input.actions_for_key(arcade.key.M) == []
    assert app.settings.input.mapping["map"] == ["N"]
    d.press("esc")  # back to main settings
    assert d.scene.mode == "main"
    d.press("esc")
    assert d.scene_name() == "MainMenuScene"


def test_records_and_profile_switch(app, tmp_path, monkeypatch):
    from amormortuorum.core import settings as settings_mod
    from amormortuorum.scenes import profiles as profiles_scene

    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "user_settings_path", lambda: target)
    monkeypatch.setattr(profiles_scene, "user_settings_path", lambda: target)

    d = Driver(app)
    d.boot_to_menu()
    # Starting a run counts; so does walking
    d.press("enter")  # New Run
    assert app.state.meta.stats.get("runs_started") == 1
    d.press("enter")  # Enter the Dungeon
    d.press("right")
    d.press("left")
    assert app.state.meta.stats.get("steps", 0) >= 1
    d.press("esc")
    while d.scene.pause_menu.current.label != "Abandon run":
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "MainMenuScene"

    while d.scene.menu.current.label != "Records":
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "RecordsScene"
    d.press("esc")

    while not d.scene.menu.current.label.startswith("Profile:"):
        d.press("down")
    d.press("enter")
    assert d.scene_name() == "ProfilesScene"
    while d.scene.menu.current.label != "New profile":
        d.press("down")
    d.press("enter")
    assert app.state.save_manager.profile_id == "profile2"
    assert app.state.meta.stats == {}  # fresh profile
    assert app.settings.game.profile == "profile2"
    assert target.exists()
    d.press("esc")
    assert any(it.label == "Profile: profile2" for it in d.scene.menu.items)
    # Switching back restores the first profile's counters
    while not d.scene.menu.current.label.startswith("Profile:"):
        d.press("down")
    d.press("enter")
    while not d.scene.menu.current.label.startswith("play"):
        d.press("down")
    d.press("enter")
    assert app.state.save_manager.profile_id == "play"
    assert app.state.meta.stats.get("runs_started") == 1


def test_wandering_monster_chases_then_engages(app):
    """A visible monster closes in each step; bumping into it opens combat and kills it."""
    from amormortuorum.systems.monsters import Monster, distance_field

    d = Driver(app)
    d.boot_to_menu()
    d.press("enter")  # New Run
    d.press("enter")  # Enter the Dungeon
    assert d.scene_name() == "DungeonScene"
    scene = d.scene
    fmap = scene.fmap

    # Place one fast monster on a visible tile 3-5 steps away; clear the rest.
    field = distance_field(fmap, scene.pos, 5)
    spot = next(
        p for p, dist in sorted(field.items(), key=lambda kv: -kv[1])
        if 3 <= dist <= 5 and p in scene.vis.visible and p != fmap.stairs
        and p not in fmap.chests
    )
    monster = Monster(id=99, pos=spot, enemies=("skel_basic",), name="Skeleton", spd=99)
    scene.monsters[:] = [monster]
    scene._mon_rng.random()  # any state is fine; the chase is deterministic
    scene._refresh_monsters()
    assert monster in scene._visible_monsters()

    old_pos = monster.pos
    # Step somewhere: the monster takes its turn and ends closer to where we now stand.
    for key in ("left", "right", "up", "down"):
        start = scene.pos
        d.press(key)
        if d.scene_name() != "DungeonScene" or scene.pos != start:
            break
    if d.scene_name() == "DungeonScene":
        assert monster.chasing
        now = distance_field(fmap, scene.pos, 12)
        assert now.get(monster.pos, 99) < now.get(old_pos, 99) or monster.pos == scene.pos
        assert "prowls" in " ".join(scene.hud.messages)
        # Keep stepping until it catches us or we walk into it
        for _ in range(8):
            if d.scene_name() == "CombatScene":
                break
            tx, ty = monster.pos
            px, py = scene.pos
            dx = (tx > px) - (tx < px)
            dy = (ty > py) - (ty < py)
            key = "right" if dx > 0 else "left" if dx < 0 else "up" if dy > 0 else "down"
            d.press(key)
    assert d.scene_name() == "CombatScene"
    assert [e.def_id for e in scene.active_battle.enemies] == ["skel_basic"]
    d.fight_until_done()
    if d.scene_name() == "DungeonScene":
        assert monster.id not in {m.id for m in scene.monsters}
        assert monster not in scene._visible_monsters()
        # Minimap draws the (now absent) monsters without error
        d.frame()
