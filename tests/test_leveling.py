from amor.progression.leveling import Character, LevelingSystem, Stats
from amor.progression.xp_curve import XPCurve


def expected_increments_for_level(L: int):
    # From leveling rules in GrowthConfig
    hp = 10 + (L // 2)
    mp = 3 + (L // 3)
    atk = 2 + (1 if (L + 1) % 5 == 0 else 0)
    defense = 2 + (1 if (L + 1) % 5 == 0 else 0)
    magic = 2 + (1 if (L + 1) % 5 == 0 else 0)
    resistance = 2 + (1 if (L + 1) % 5 == 0 else 0)
    speed = 1 + (1 if (L + 1) % 3 == 0 else 0)
    luck = 1 if (L + 1) % 2 == 0 else 0
    return dict(max_hp=hp, max_mp=mp, atk=atk, defense=defense, magic=magic, resistance=resistance, speed=speed, luck=luck)


def test_leveling_two_levels_and_stat_growth():
    curve = XPCurve.generate_parametric(25, 1.12, 99)
    lvl = LevelingSystem(curve)

    base_stats = Stats(30, 10, 5, 5, 3, 3, 4, 1)
    hero = Character(name="Hero", stats=base_stats)

    xp_needed = curve.xp_to_next(1) + curve.xp_to_next(2)
    assert xp_needed == 25 + 28

    res = lvl.add_xp(hero, xp_needed + 7)  # 60 XP -> level 3 with 7 XP into L3
    assert hero.level == 3
    assert res.levels_gained == 2
    assert res.remaining_xp_to_next == curve.total_xp_for_level(4) - hero.total_xp

    # Compute expected stat increases for L1->2 and L2->3
    inc1 = expected_increments_for_level(1)
    inc2 = expected_increments_for_level(2)

    assert hero.stats.max_hp == 30 + inc1["max_hp"] + inc2["max_hp"]
    assert hero.stats.max_mp == 10 + inc1["max_mp"] + inc2["max_mp"]
    assert hero.stats.atk == 5 + inc1["atk"] + inc2["atk"]
    assert hero.stats.defense == 5 + inc1["defense"] + inc2["defense"]
    assert hero.stats.magic == 3 + inc1["magic"] + inc2["magic"]
    assert hero.stats.resistance == 3 + inc1["resistance"] + inc2["resistance"]
    assert hero.stats.speed == 4 + inc1["speed"] + inc2["speed"]
    assert hero.stats.luck == 1 + inc1["luck"] + inc2["luck"]
