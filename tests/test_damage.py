from amormortuorum.core.rng import RNG
from amormortuorum.combat.damage import compute_damage


def test_damage_determinism_no_crit():
    rng = RNG(seed=12345)
    res1 = compute_damage(50, 20, rng, crit_chance=0.0, variance=(0.9, 0.9))
    # With fixed variance and no crit, the result should be deterministic
    assert res1.damage == int((max(1, 50 - 20)) * 0.9)
    assert res1.is_crit is False


def test_high_defense_min_damage():
    rng = RNG(seed=1)
    res = compute_damage(10, 100, rng, crit_chance=0.0, variance=(0.85, 1.0))
    assert res.damage >= 1


def test_crit_applies_multiplier():
    rng = RNG(seed=99)
    # Eliminate variance by using (1.0, 1.0) and force crit by 100% chance
    res = compute_damage(30, 10, rng, crit_chance=1.0, crit_multiplier=2.0, variance=(1.0, 1.0))
    expected_base = max(1, 30 - 10)
    expected = int(round(expected_base * 2.0))
    assert res.is_crit is True
    assert res.damage == expected


def test_invalid_params_raise():
    rng = RNG(seed=0)
    try:
        compute_damage(-1, 0, rng)
    except ValueError:
        pass
    else:
        assert False

    try:
        compute_damage(1, -2, rng)
    except ValueError:
        pass
    else:
        assert False

    try:
        compute_damage(1, 1, rng, crit_chance=1.5)
    except ValueError:
        pass
    else:
        assert False

    try:
        compute_damage(1, 1, rng, variance=(1.0, 0.5))
    except ValueError:
        pass
    else:
        assert False

    try:
        compute_damage(1, 1, rng, defense_mitigation=-0.1)
    except ValueError:
        pass
    else:
        assert False
