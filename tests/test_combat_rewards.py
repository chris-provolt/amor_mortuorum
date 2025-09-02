from amor.combat.rewards import Enemy, BattleResult, apply_battle_xp
from amor.progression.leveling import Character
from amor.progression.xp_curve import XPCurve
from amor.progression.leveling import LevelingSystem


def test_battle_xp_distribution_and_leveling():
    curve = XPCurve.generate_parametric(25, 1.12, 99)
    leveling = LevelingSystem(curve)

    party = [
        Character(name="A"),
        Character(name="B"),
        Character(name="C", alive=False),  # should not receive XP when alive_only=True
    ]

    enemies = [Enemy("Slime", 40), Enemy("Bat", 30)]  # total 70 XP
    result = BattleResult(enemies=enemies)

    awards = apply_battle_xp(leveling, party, result, alive_only=True)

    # Only A and B receive XP, split evenly: 35 each
    assert awards["A"][0] == 35
    assert awards["B"][0] == 35
    assert awards["C"][0] == 0

    # A and B should be level 2 with 10 XP into level 2 (since 25 needed to reach 2)
    assert party[0].level == 2
    assert party[1].level == 2

    # Verify that the remaining XP to next matches expectations
    remaining_to_3 = curve.total_xp_for_level(3) - party[0].total_xp
    # total_xp for A: 35; thresholds: lvl2=25, lvl3=53 -> remaining 18
    assert remaining_to_3 == 18
