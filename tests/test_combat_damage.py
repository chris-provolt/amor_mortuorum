import sys
import pathlib

# Ensure 'src' is on the import path for test execution in varied environments
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import random

from amormortuorum.combat.damage import DamageCalculator
from amormortuorum.combat.engine import CombatEngine
from amormortuorum.combat.entities import Combatant


def test_attack_reduces_hp_without_kill():
    rng = random.Random(1337)
    # Use zero variance for deterministic base damage testing
    engine = CombatEngine(DamageCalculator(variance=0.0))

    attacker = Combatant(name="Hero", max_hp=50, hp=50, atk=10, df=2)
    defender = Combatant(name="Goblin", max_hp=30, hp=30, atk=5, df=3)

    # base damage = max(1, atk - df) = 10 - 3 = 7
    result = engine.attack(attacker, defender, rng=rng)
    assert result.damage == 7
    assert result.defender_hp_before == 30
    assert result.defender_hp_after == 23
    assert result.defeated is False


def test_min_damage_floor_is_one():
    rng = random.Random(42)
    engine = CombatEngine(DamageCalculator(variance=0.0))

    attacker = Combatant(name="Weakling", max_hp=10, hp=10, atk=1, df=0)
    defender = Combatant(name="Tank", max_hp=20, hp=20, atk=0, df=999)

    result = engine.attack(attacker, defender, rng=rng)
    # base = max(1, 1 - 999) = 1, variance 0 => 1
    assert result.damage == 1
    assert defender.hp == 19


def test_rng_variation_within_expected_bounds():
    rng = random.Random(314159)
    # Variance 10%
    calc = DamageCalculator(variance=0.10)
    base = 20 - 5  # atk - df = 15

    # Perform several rolls and ensure damage is within [13.5, 16.5] rounded, with floor at 1
    damages = [calc.compute_damage(20, 5, rng) for _ in range(10)]

    for dmg in damages:
        assert dmg >= 1
        # Bounds after rounding; 15 * 0.9 = 13.5, 15 * 1.1 = 16.5 -> ints in [14, 16]
        assert 14 <= dmg <= 16


def test_death_sets_hp_zero_and_is_logged():
    rng = random.Random(7)
    engine = CombatEngine(DamageCalculator(variance=0.0))

    attacker = Combatant(name="Hero", max_hp=50, hp=50, atk=999, df=0)
    defender = Combatant(name="Slime", max_hp=10, hp=10, atk=1, df=0)

    result = engine.attack(attacker, defender, rng=rng)
    assert result.damage >= 10
    assert defender.hp == 0  # death sets HP to exactly 0
    assert result.defeated is True

    # Check a defeat event was logged
    events = [e for e in engine.log.events() if e.type == "defeat"]
    assert any("Slime was defeated by Hero" in e.message for e in events)


def test_no_action_if_attacker_is_defeated():
    rng = random.Random(1)
    engine = CombatEngine(DamageCalculator(variance=0.0))

    attacker = Combatant(name="KO'd", max_hp=20, hp=0, atk=50, df=0)
    defender = Combatant(name="Target", max_hp=20, hp=20, atk=1, df=1)

    result = engine.attack(attacker, defender, rng=rng)
    assert result.damage == 0
    assert defender.hp == 20  # unchanged
    assert result.defeated is False
