import pytest

from amor.game.game_state import GameState
from amor.game.entities import Actor
from amor.game.traps import SpikeTrap, DartTrap
from amor.game.constants import RIGHT


def test_spike_trap_damage_on_enter():
    game = GameState(10, 10)
    # Register SFX keys to emulate available assets
    game.audio.register_sfx("trap_spike")
    game.audio.register_sfx("trap_dart")

    hero = Actor("hero", "Hero", 1, 1, max_hp=10)
    game.add_entity(hero)

    spike = SpikeTrap(tid="sp1", x=2, y=1, damage=3)
    game.add_trap(spike)

    moved = game.move_entity(hero, 1, 0)  # to (2,1)
    assert moved is True
    assert hero.hp == 7  # 10 - 3

    # Notification present
    notes = [e for e in game.bus.history if e.get("type") == "notification"]
    assert any("Spikes" in e["message"] for e in notes)

    # SFX played if present
    assert "trap_spike" in game.audio.played


def test_dart_trap_fires_on_los_hits_entity():
    game = GameState(10, 10)
    game.audio.register_sfx("trap_dart")
    hero = Actor("hero", "Hero", 3, 1, max_hp=10)
    game.add_entity(hero)

    dart = DartTrap(tid="d1", x=1, y=1, direction=RIGHT, period_ticks=10, dart_damage=4, max_range=8)
    game.add_trap(dart)

    # Immediate LOS -> fires this tick
    game.tick()
    assert hero.hp == 6  # 10 - 4

    # Event records a hit
    fired = [e for e in game.bus.history if e.get("type") == "trap_fired" and e.get("trap_id") == "d1"]
    assert any(e.get("hit") is True for e in fired)
    assert "trap_dart" in game.audio.played


def test_dart_trap_timer_fire_when_no_los_then_hits_if_target_enters_path():
    game = GameState(10, 10)
    game.audio.register_sfx("trap_dart")
    hero = Actor("hero", "Hero", 5, 2, max_hp=10)  # off the firing row initially
    game.add_entity(hero)

    dart = DartTrap(tid="d2", x=1, y=2, direction=RIGHT, period_ticks=2, dart_damage=2, max_range=10)
    game.add_trap(dart)

    # Tick 1: no LOS; cooldown -> 1
    game.tick()
    assert hero.hp == 10

    # Move hero into line on Tick 2; cooldown reaches 0 and fires -> should hit now
    moved = game.move_entity(hero, -2, 0)  # from (5,2) to (3,2)
    assert moved
    game.tick()
    assert hero.hp == 8  # took 2 damage

    # Verify fired event was emitted
    fired = [e for e in game.bus.history if e.get("type") == "trap_fired" and e.get("trap_id") == "d2"]
    assert any(e.get("hit") is True for e in fired)


def test_dart_projectile_stops_on_wall_no_damage():
    game = GameState(10, 10)
    game.audio.register_sfx("trap_dart")

    # Place a wall between trap and hero
    game.map.set_wall(2, 1, True)

    hero = Actor("hero", "Hero", 3, 1, max_hp=10)
    game.add_entity(hero)

    dart = DartTrap(tid="d3", x=1, y=1, direction=RIGHT, period_ticks=1, dart_damage=5, max_range=10)
    game.add_trap(dart)

    # Tick 1: LOS blocked by wall; cooldown -> 0 and fires, but wall blocks -> no hit
    game.tick()
    assert hero.hp == 10

    # Fired event exists with hit False
    fired = [e for e in game.bus.history if e.get("type") == "trap_fired" and e.get("trap_id") == "d3"]
    assert any(e.get("hit") is False for e in fired)
