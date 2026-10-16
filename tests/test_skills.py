from random import Random

import pytest

from amormortuorum.data import DataError, GameData
from amormortuorum.errors import InvalidOperation
from amormortuorum.systems.combat import Action, ActionKind, Battle, Outcome
from amormortuorum.systems.entities import Enemy, new_player
from amormortuorum.systems.progression import grant_xp


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def test_skills_load_and_learn_by_level(data):
    assert [sk.id for sk in data.skills_known_at(1)] == ["ember"]
    assert [sk.id for sk in data.skills_known_at(4)] == ["ember", "mend", "grave_frost"]
    assert data.skill("dirge").target == "all_enemies"
    with pytest.raises(DataError):
        data.skill("fireball")
    p = new_player()
    assert [sk.id for sk in p.known_skills(data)] == ["ember"]
    grant_xp(p, data.xp_curve.xp_for_level(2), data)
    assert "mend" in [sk.id for sk in p.known_skills(data)]


def test_bad_skill_data_rejected(data):
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "src" / "amormortuorum" / "data"

    def read(name):
        return json.loads((folder / name).read_text(encoding="utf-8"))

    raw = dict(
        items=read("items.json"), enemies=read("enemies.json"),
        loot_tables=read("loot_tables.json"), floor_tiers=read("floor_tiers.json"),
        relics=read("relics.json"), encounters=read("encounters.json"), shop=read("shop.json"),
        xp_curve=read("xp_curve.json"), bosses=read("bosses.json"),
    )
    raw["skills"] = [{"id": "x", "name": "x", "mp": 1, "target": "ally", "damage": 5}]
    with pytest.raises(DataError, match="target"):
        GameData.from_raw(**raw)
    raw["skills"] = [{"id": "x", "name": "x", "mp": 1, "target": "enemy"}]
    with pytest.raises(DataError, match="exactly one"):
        GameData.from_raw(**raw)


def test_offensive_skill_spends_mp_and_ignores_defence(data):
    hero = new_player()
    foe = Enemy.from_def(data.enemy("bone_guard"))  # df 5, hp 20
    battle = Battle([hero], [foe], Random(1), data)
    mp = hero.stats.mp
    events = battle.submit(Action(ActionKind.SKILL, 0, skill_id="ember"))
    assert hero.stats.mp == mp - data.skill("ember").mp
    assert any("casts Ember" in e.text for e in events)
    assert foe.stats.hp == 20 - (data.skill("ember").damage + hero.level)


def test_skill_validation(data):
    hero = new_player()
    foe = Enemy.from_def(data.enemy("skel_basic"))
    battle = Battle([hero], [foe], Random(1), data)
    with pytest.raises(InvalidOperation, match="not learned"):
        battle.submit(Action(ActionKind.SKILL, 0, skill_id="oblivion_bolt"))
    hero.stats.mp = 0
    with pytest.raises(InvalidOperation, match="MP"):
        battle.submit(Action(ActionKind.SKILL, 0, skill_id="ember"))
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.SKILL, 0))


def test_healing_and_multi_target_skills(data):
    hero = new_player()
    grant_xp(hero, data.xp_curve.xp_for_level(7), data)  # knows mend and dirge
    hero.stats.mp = hero.stats.max_mp = 50
    hero.take_damage(15)
    foes = [Enemy.from_def(data.enemy("skel_basic")) for _ in range(3)]
    battle = Battle([hero], foes, Random(2), data)

    mp = hero.stats.mp
    events = battle.submit(Action(ActionKind.SKILL, 0, skill_id="mend"))
    heal = next(e for e in events if "casts Mend" in e.text)
    assert "recovers 15 HP" in heal.text
    assert hero.stats.mp == mp - data.skill("mend").mp

    before = [f.stats.hp for f in foes]
    events = battle.submit(Action(ActionKind.SKILL, 0, skill_id="dirge"))
    hits = [e for e in events if "Dirge" in e.text and "for" in e.text]
    assert len(hits) == 3
    assert all(f.stats.hp < b for f, b in zip(foes, before))
    assert battle.outcome in (Outcome.ONGOING, Outcome.VICTORY)


def test_mp_tonic_restores_mp_in_and_out_of_combat(data):
    hero = new_player()
    hero.stats.mp = 1
    tonic = data.item("tonic_mind")
    assert tonic.usable_in_combat
    hero.inventory.add(tonic, 2)
    assert hero.use_consumable(tonic) == 0  # no HP healed
    assert hero.stats.mp == min(hero.stats.max_mp, 1 + tonic.mp_restore)

    hero.stats.mp = 0
    foe = Enemy.from_def(data.enemy("skel_basic"))
    battle = Battle([hero], [foe], Random(3), data)
    events = battle.submit(Action(ActionKind.ITEM, 0, item_id="tonic_mind"))
    assert any("regains" in e.text for e in events)
    assert hero.stats.mp == tonic.mp_restore
    assert hero.inventory.count("tonic_mind") == 0


def test_events_name_their_skill_or_item(data):
    hero = new_player()
    grant_xp(hero, data.xp_curve.xp_for_level(7), data)
    hero.stats.mp = hero.stats.max_mp = 50
    hero.take_damage(10)
    hero.inventory.add(data.item("scroll_embers"), 1)
    hero.inventory.add(data.item("potion_small"), 1)
    foes = [Enemy.from_def(data.enemy("skel_basic")) for _ in range(2)]
    for foe in foes:  # sturdy enough to survive the whole exchange
        foe.stats.hp = foe.stats.max_hp = 500
    battle = Battle([hero], foes, Random(3), data)
    events = battle.submit(Action(ActionKind.SKILL, 0, skill_id="dirge"))
    cast = next(e for e in events if e.effect == "cast")
    assert cast.source == "dirge"
    assert [e.source for e in events if e.effect == "spell"] == ["dirge", "dirge"]
    events = battle.submit(Action(ActionKind.SKILL, 0, skill_id="mend"))
    assert next(e for e in events if e.effect == "heal").source == "mend"
    events = battle.submit(Action(ActionKind.ITEM, 0, target=0, item_id="scroll_embers"))
    assert next(e for e in events if e.effect == "spell").source == "scroll_embers"
    events = battle.submit(Action(ActionKind.ITEM, 0, item_id="potion_small"))
    assert next(e for e in events if e.effect == "heal").source == "potion_small"
    assert all(e.source == "" for e in events if e.effect == "slash")
