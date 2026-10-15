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
def app(tmp_path):
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

    def fight_until_done(self, max_rounds: int = 60):
        """Attack every round until the combat scene pops."""
        for _ in range(max_rounds):
            if self.scene_name() != "CombatScene":
                return
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
        if driver.scene_name() == "CombatScene":
            driver.fight_until_done()
        if driver.scene_name() != "DungeonScene":
            return  # died (summary) or left the floor
        scene = driver.scene
        dx, dy = nxt[0] - scene.pos[0], nxt[1] - scene.pos[1]
        driver.press({(1, 0): "right", (-1, 0): "left", (0, 1): "up", (0, -1): "down"}[(dx, dy)])


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
