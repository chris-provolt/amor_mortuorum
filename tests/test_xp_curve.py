import os

from amor.progression.xp_curve import XPCurve


def test_parametric_xp_curve_loading():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "xp_curve.json")
    curve = XPCurve.from_file(path)
    # Level 1 -> 2
    assert curve.xp_to_next(1) == 25
    # Level 2 -> 3: round(25 * 1.12) = 28
    assert curve.xp_to_next(2) == 28
    # Level 3 -> 4: round(25 * 1.12^2)
    assert curve.xp_to_next(3) == int(round(25 * (1.12 ** 2)))
    # Monotonic cumulative thresholds
    assert curve.total_xp_for_level(1) == 0
    assert curve.total_xp_for_level(2) == 25
    assert curve.total_xp_for_level(3) == 25 + 28
    assert curve.max_level == 99
