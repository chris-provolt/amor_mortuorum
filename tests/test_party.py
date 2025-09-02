import pytest

from amor.core.party import Party, PartyMember
from amor.core.stats import Stats


def make_member(name: str, hp: int = 10, spd: int = 10) -> PartyMember:
    return PartyMember(name=name, stats=Stats(hp=hp, max_hp=hp, spd=spd))


def test_party_initialization_and_slots():
    p = Party()
    assert len(p.slots) == 4
    assert list(p.slots) == [None, None, None, None]

    # Initialize with some members and None slots
    a, b = make_member("Alice"), make_member("Bob")
    p2 = Party([a, None, b])
    assert p2.get_slot(0) == a
    assert p2.get_slot(1) is None
    assert p2.get_slot(2) == b
    assert p2.get_slot(3) is None


def test_add_member_auto_and_explicit_slot():
    p = Party()
    a, b, c, d = make_member("A"), make_member("B"), make_member("C"), make_member("D")

    # Auto-fill
    s0 = p.add_member(a)
    assert s0 == 0 and p.get_slot(0) == a

    # Place explicitly into slot 2
    s2 = p.add_member(b, slot=2)
    assert s2 == 2 and p.get_slot(2) == b

    # Fill remaining
    assert p.add_member(c) == 1
    assert p.add_member(d) == 3

    # Now full
    with pytest.raises(ValueError):
        p.add_member(make_member("E"))


def test_add_member_errors_on_occupied_or_duplicate():
    p = Party()
    a, b = make_member("A"), make_member("B")
    p.add_member(a, slot=1)
    with pytest.raises(ValueError):
        p.add_member(b, slot=1)  # occupied
    with pytest.raises(ValueError):
        p.add_member(a)  # duplicate


def test_remove_member_by_index_and_instance():
    p = Party()
    a, b = make_member("A"), make_member("B")
    p.add_member(a)
    p.add_member(b)

    idx = p.remove_member(a)
    assert idx == 0 and p.get_slot(0) is None and p.get_slot(1) == b

    idx2 = p.remove_member(1)
    assert idx2 == 1 and p.get_slot(1) is None

    with pytest.raises(ValueError):
        p.remove_member(1)  # already empty

    with pytest.raises(ValueError):
        p.remove_member(a)  # not in party anymore

    with pytest.raises(IndexError):
        p.remove_member(5)  # invalid index


def test_iteration_and_active_members():
    p = Party()
    a, b, c = make_member("A"), make_member("B"), make_member("C")
    p.add_member(a)
    p.add_member(b, slot=3)
    # Iteration yields present members in slot order
    names = [m.name for m in p]
    assert names == ["A", "B"]

    # Active members excludes dead
    c.stats.hp = 0
    p.add_member(c, slot=1)
    active = [m.name for m in p.iter_active_members()]
    assert active == ["A", "B"]


def test_slot_views_include_empty_slots():
    p = Party()
    a = make_member("Alice", hp=25)
    p.add_member(a, slot=2)

    views = p.as_slot_views()
    assert len(views) == 4
    assert views[0].is_empty is True
    assert views[1].is_empty is True
    assert views[2].is_empty is False and views[2].name == "Alice" and views[2].hp == 25
    assert views[3].is_empty is True
