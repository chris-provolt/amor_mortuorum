import math

import pytest

from amormortuorum.combat.models import Actor, Party
from amormortuorum.combat.actions import AttackAction, DefendAction, FleeAction
from amormortuorum.utils.random_provider import RandomProvider
from amormortuorum.config import CombatConfig


def test_defend_reduces_next_hit_once():
    # Setup
    hero = Actor(name="Hero", max_hp=100, spd=10)
    goblin = Actor(name="Goblin", max_hp=30, spd=8)

    # Hero defends
    DefendAction().execute(hero)

    # Goblin attacks with 10 damage; defend halves to 5
    dmg1 = AttackAction(10).execute(goblin, hero)
    assert dmg1 == 5
    assert hero.hp == 95

    # Next attack should be full damage since defend is consumed
    dmg2 = AttackAction(10).execute(goblin, hero)
    assert dmg2 == 10
    assert hero.hp == 85


def test_defend_rounding_down_but_min_one():
    hero = Actor(name="Hero", max_hp=50, spd=10)
    DefendAction().execute(hero)

    # 1 damage halved would be 0.5 -> floor to 0, but enforce min 1 when damage>0
    dmg = AttackAction(1).execute(Actor("Dummy", 10, 1), hero)
    assert dmg == 1
    assert hero.hp == 49


@pytest.mark.parametrize(
    "party_spds, enemy_spds, expected_relation",
    [
        ([10, 10], [10, 10], "around_base"),
        ([20, 20], [10, 10], "high"),
        ([5, 5], [10, 10], "low"),
    ],
)
def test_flee_probability_scales_with_spd(party_spds, enemy_spds, expected_relation):
    cfg = CombatConfig.default()

    party = Party(
        name="Heroes",
        members=[Actor(name=f"H{i}", max_hp=10, spd=spd) for i, spd in enumerate(party_spds)],
    )
    enemies = Party(
        name="Baddies",
        members=[Actor(name=f"E{i}", max_hp=10, spd=spd) for i, spd in enumerate(enemy_spds)],
    )

    # Use a deterministic RNG, but we will control the roll explicitly
    rng = RandomProvider(seed=42)
    action = FleeAction(rng)

    # Access the internal probability function deterministically for testing
    p = action._probability(party, enemies)

    if expected_relation == "around_base":
        assert math.isclose(p, cfg.flee_base, rel_tol=0.0, abs_tol=0.05)
    elif expected_relation == "high":
        assert p > cfg.flee_base
    elif expected_relation == "low":
        assert p < cfg.flee_base

    # Now test success/failure deterministically by injecting a roll vs p
    # We emulate the roll by setting rng to known sequence via monkeypatching the method
    class R:
        def __init__(self, value):
            self.value = value
        def random(self):
            return self.value

    # Success when roll < p
    action.rng = R(max(0.0, p - 1e-6))
    result = action.attempt(party, enemies)
    assert result.success is True
    assert math.isclose(result.probability, p)

    # Failure when roll > p
    action.rng = R(min(1.0, p + 1e-6))
    result = action.attempt(party, enemies)
    assert result.success is False


def test_flee_bounds_and_auto_success():
    cfg = CombatConfig.default()

    # Extreme fast party vs very slow enemies -> near max
    party_fast = Party("Fasties", [Actor("F", 10, 999)])
    enemies_slow = Party("Slows", [Actor("S", 10, 1)])
    p = FleeAction(RandomProvider(1))._probability(party_fast, enemies_slow)
    assert cfg.flee_min <= p <= cfg.flee_max
    assert p > 0.8  # should be high under defaults

    # Extreme slow party vs very fast enemies -> near min
    party_slow = Party("Slows", [Actor("S", 10, 1)])
    enemies_fast = Party("Fasts", [Actor("F", 10, 999)])
    p2 = FleeAction(RandomProvider(1))._probability(party_slow, enemies_fast)
    assert cfg.flee_min <= p2 <= cfg.flee_max
    assert p2 <= cfg.flee_base

    # No enemies alive -> auto success
    enemies_dead = Party("Gone", [Actor("E", 10, 5)])
    for m in enemies_dead.members:
        m.hp = 0
    p3 = FleeAction(RandomProvider(1))._probability(party_fast, enemies_dead)
    assert p3 == 1.0


def test_invalid_defend_multiplier_raises():
    hero = Actor("Hero", 10, 5)
    with pytest.raises(ValueError):
        hero.apply_defend(0.0)
    with pytest.raises(ValueError):
        hero.apply_defend(1.1)


def test_attack_negative_damage_raises():
    hero = Actor("Hero", 10, 5)
    goblin = Actor("Goblin", 10, 3)
    with pytest.raises(ValueError):
        AttackAction(-1).execute(hero, goblin)
