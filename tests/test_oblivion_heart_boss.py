from __future__ import annotations

from pathlib import Path

from amor_mortuorum.bosses.oblivion_heart import OHConfig, build_oblivion_heart
from amor_mortuorum.core.events import EventBus
from amor_mortuorum.core.save import InMemorySaveService
from amor_mortuorum.combat.actors import Actor, Party


def make_boss():
    cfg = OHConfig.from_json(Path(__file__).parents[1] / "data" / "bosses" / "oblivion_heart.json")
    bus = EventBus()
    save = InMemorySaveService()
    boss = build_oblivion_heart(cfg, bus, save)
    boss.start_battle()
    return boss, bus, save


def test_phase_transitions_and_music_sfx():
    boss, bus, _ = make_boss()

    # On start, phase1 music/sfx should be published
    assert any(e.type == "music.change" and e.payload.get("track") == "music.oblivion_heart.phase1" for e in bus.history)
    assert any(e.type == "sfx.play" and e.payload.get("key") == "sfx.boss.oblivion_heart.phase1" for e in bus.history)

    # Drop to 65% -> phase 2
    boss.hp = int(boss.max_hp * 0.65)
    boss.update_phase_if_needed()
    assert any(e.type == "music.change" and e.payload.get("track") == "music.oblivion_heart.phase2" for e in bus.history)
    assert any(e.type == "sfx.play" and e.payload.get("key") == "sfx.boss.oblivion_heart.phase2" for e in bus.history)

    # Drop to 15% -> phase 3 (enrage)
    boss.hp = int(boss.max_hp * 0.15)
    boss.update_phase_if_needed()
    assert any(e.type == "music.change" and e.payload.get("track") == "music.oblivion_heart.enraged" for e in bus.history)
    assert any(e.type == "sfx.play" and e.payload.get("key") == "sfx.boss.oblivion_heart.enrage" for e in bus.history)
    assert boss.status.get("enraged") is True


def test_self_heal_check_in_phase2():
    boss, bus, _ = make_boss()
    # Move to phase 2 by reducing HP
    boss.hp = int(boss.max_hp * 0.65)
    boss.update_phase_if_needed()

    # Put boss at 35% to trigger self-heal check, ensure cooldown ready
    boss.hp = int(boss.max_hp * 0.35)
    boss.cooldowns.clear()

    party = Party([Actor("Hero", 1200, 1200), Actor("Mage", 800, 800)])

    before = boss.hp
    res = boss.take_turn(party)
    assert res["type"] in ("heal", "multi")
    assert boss.hp > before  # healed
    assert any(e.type == "sfx.play" and e.payload.get("key") == "sfx.boss.reconstitution" for e in bus.history)


def test_enrage_aoe_cataclysm_and_combo():
    boss, bus, _ = make_boss()
    # Force phase 3
    boss.hp = int(boss.max_hp * 0.15)
    boss.update_phase_if_needed()

    party = Party([Actor("Hero", 1200, 1200), Actor("Mage", 800, 800), Actor("Rogue", 900, 900)])

    # First turn in p3 should use Cataclysmic Beat if cooldown 0
    boss.cooldowns["cataclysm"] = 0
    res = boss.take_turn(party)
    assert res["name"] == "Cataclysmic Beat"
    # Everyone should take damage
    assert all(m.hp < m.max_hp for m in party.members)

    # Next turn: cooldown prevents cataclysm; expect combo or heal depending on HP
    # Raise HP a bit to avoid heal
    boss.hp = max(boss.hp, int(boss.max_hp * 0.3))
    res2 = boss.take_turn(party)
    assert res2["name"] in ("Ravenous Combo", "Cataclysmic Beat")


def test_clear_condition_recorded_on_defeat():
    boss, bus, save = make_boss()
    # Kill the boss
    boss.receive_damage(boss.hp)
    assert save.get_flag("boss.b99.cleared") is True
    assert save.has_relic("relic.final.oblivion_heart") is True
    # Death SFX and music stop published
    assert any(e.type == "sfx.play" and e.payload.get("key") == "sfx.boss.death" for e in bus.history)
    assert any(e.type == "music.stop" for e in bus.history)
