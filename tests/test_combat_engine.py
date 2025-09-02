from amor.core.party import Party, PartyMember
from amor.core.stats import Stats
from amor.combat.engine import CombatEngine, SimpleEnemy


def make_member(name: str, spd: int, hp: int = 10) -> PartyMember:
    return PartyMember(name=name, stats=Stats(hp=hp, max_hp=hp, spd=spd))


def test_combat_turn_order_uses_current_party():
    # Party with 2 members, 2 empty slots
    p = Party()
    m1 = make_member("Alice", spd=12)
    m2 = make_member("Bob", spd=8)
    p.add_member(m1, slot=0)
    p.add_member(m2, slot=3)

    # Enemy
    e1 = SimpleEnemy(name="Slime", spd=10)

    engine = CombatEngine()
    order = engine.build_turn_order(p, [e1])
    names = [a.name for a in order]

    # SPD: Alice(12), Slime(10), Bob(8)
    assert names == ["Alice", "Slime", "Bob"]


def test_dead_party_members_are_skipped():
    p = Party()
    a = make_member("Alice", spd=12)
    b = make_member("Bob", spd=14)
    p.add_member(a)
    p.add_member(b)

    # Kill Bob; he should be skipped
    b.stats.hp = 0

    e = SimpleEnemy(name="Imp", spd=9)
    engine = CombatEngine()
    order = engine.build_turn_order(p, [e])
    names = [a.name for a in order]

    # Bob dead -> not present; SPD: Alice(12) vs Imp(9)
    assert names == ["Alice", "Imp"]


def test_run_round_returns_action_tuples():
    p = Party()
    a = make_member("A", spd=5)
    b = make_member("B", spd=7)
    p.add_member(a)
    p.add_member(b)
    e = SimpleEnemy(name="Gob", spd=6)

    engine = CombatEngine()
    actions = engine.run_round(p, [e])
    # Order: B(7), Gob(6), A(5)
    assert [n for n, _ in actions] == ["B", "Gob", "A"]
    assert all(desc == "acts" for _, desc in actions)
