from amor.core.party import Party, PartyMember
from amor.core.stats import Stats
from amor.ui.hud.party_hud import PartyHUDModelBuilder


def make_member(name: str, hp: int = 15, mp: int = 3, spd: int = 10) -> PartyMember:
    return PartyMember(name=name, stats=Stats(hp=hp, max_hp=hp, mp=mp, max_mp=mp, spd=spd))


def test_party_hud_model_includes_empty_slots():
    p = Party()
    alice = make_member("Alice")
    bob = make_member("Bob")

    p.add_member(alice, slot=1)
    p.add_member(bob, slot=3)

    builder = PartyHUDModelBuilder()
    model = builder.build(p)

    assert len(model) == 4
    # Slot 0 empty
    assert model[0].is_empty is True
    assert model[0].name != "Alice" and model[0].name != "Bob"

    # Slot 1 Alice
    assert model[1].is_empty is False
    assert model[1].name == "Alice"
    assert model[1].hp_text.startswith("15/")

    # Slot 2 empty
    assert model[2].is_empty is True

    # Slot 3 Bob
    assert model[3].is_empty is False
    assert model[3].name == "Bob"


def test_party_hud_marks_dead_members():
    p = Party()
    a = make_member("Alice")
    a.stats.hp = 0
    p.add_member(a, slot=0)

    builder = PartyHUDModelBuilder()
    model = builder.build(p)

    assert model[0].is_dead is True
    assert model[0].is_empty is False
