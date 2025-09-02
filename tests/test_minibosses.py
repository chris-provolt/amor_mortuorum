import pytest

from amor_mortuorum.combat.core import Entity, Stats, AttackAction, DamageEvent
from amor_mortuorum.combat.engine import BattleEngine
from amor_mortuorum.bosses.minibosses import (
    make_miniboss_shielded,
    make_miniboss_summoner,
    make_miniboss_enraged,
    make_miniboss_reflect,
)


class DummyPlayer(Entity):
    def __init__(self, name: str = "Hero", atk: int = 20, defense: int = 2, spd: int = 12):
        super().__init__(name=name, team="party", stats=Stats(max_hp=200, hp=200, atk=atk, defense=defense, spd=spd), is_player=True)


def perform_simple_battle_rounds(engine: BattleEngine, rounds: int = 1):
    engine.start_battle()
    for _ in range(rounds):
        if engine.is_battle_over():
            break
        engine.step_turn()


def test_shielded_miniboss_shield_absorbs_and_telegraphs():
    hero = DummyPlayer()
    boss = make_miniboss_shielded()
    engine = BattleEngine([hero], [boss])

    engine.start_battle()

    # Check telegraph for Aegis
    tel_texts = [t for n, t in engine.log.telegraphs if n == boss.name]
    assert any("Aegis" in t for t in tel_texts)

    # Let hero act first and attack boss
    engine.step_turn()

    # Compute naive damage without shield
    expected_raw = max(1, hero.stats.atk - boss.stats.defense)

    # Because of shield, boss should have lost strictly less than expected_raw this turn
    damage_events = [e for e in engine.log.events if "deals" in e and boss.name in e]
    assert damage_events, "There should be at least one damage event against boss"

    # Parse the first line like "Hero deals X to Boss"
    line = next(l for l in engine.log.events if f"deals" in l and boss.name in l and hero.name in l)
    dealt = int(line.split(" deals ")[1].split(" to ")[0])

    assert dealt < expected_raw, f"Shield should have absorbed some damage (dealt {dealt} < raw {expected_raw})"


def test_summoner_miniboss_chants_then_summons_adds():
    hero = DummyPlayer()
    boss = make_miniboss_summoner()
    engine = BattleEngine([hero], [boss])

    # Run two turns to hit the telegraph then the summon
    perform_simple_battle_rounds(engine, rounds=2)

    # Check telegraph
    tel_texts = [t for n, t in engine.log.telegraphs if n == boss.name]
    assert any("Chanting" in t for t in tel_texts), "Summoner should telegraph the chant"

    # Check summons appeared among enemies
    adds = [e for e in engine.enemies if e is not boss]
    assert len(adds) >= 2, "Summoner should have summoned adds"


def test_enraged_miniboss_enrages_below_threshold_and_hits_harder():
    hero = DummyPlayer()
    boss = make_miniboss_enraged()
    engine = BattleEngine([hero], [boss])

    engine.start_battle()

    # Bring boss to just below 50% HP by directly applying damage events in a controlled way
    # Attack until below threshold
    raw = max(1, hero.stats.atk - boss.stats.defense)
    while boss.stats.hp > boss.stats.max_hp // 2:
        engine.step_turn()  # hero will attack first
        if engine.is_battle_over():
            break

    # Next turn start should trigger enraged telegraph
    engine.step_turn()

    tel_texts = [t for n, t in engine.log.telegraphs if n == boss.name]
    assert any("Blood fury" in t for t in tel_texts), "Boss should telegraph Enrage"

    # Measure boss damage to hero; it should be increased compared to base
    base_damage = max(1, boss.stats.atk - hero.stats.defense)

    # Find a line where boss deals damage to hero after enraging
    late_events = [e for e in engine.log.events if f"{boss.name} deals" in e and hero.name in e]
    assert late_events, "Boss should have attacked hero"
    dealt = int(late_events[-1].split(" deals ")[1].split(" to ")[0])
    assert dealt > base_damage, f"Enrage should increase damage (dealt {dealt} > base {base_damage})"


def test_reflect_miniboss_casts_reflect_and_reflects_damage():
    hero = DummyPlayer()
    boss = make_miniboss_reflect()
    engine = BattleEngine([hero], [boss])

    perform_simple_battle_rounds(engine, rounds=1)  # Turn 1: boss should cast reflect

    tel_texts = [t for n, t in engine.log.telegraphs if n == boss.name]
    assert any("Mirror Veil" in t for t in tel_texts), "Boss should telegraph Mirror Veil"

    # Next turn, hero will hit into reflect and take reflected damage
    engine.step_turn()

    # Check a reflect line exists
    reflect_lines = [e for e in engine.log.events if "Mirror Veil reflects" in e]
    assert reflect_lines, "Reflect should have reflected damage back to the attacker"

