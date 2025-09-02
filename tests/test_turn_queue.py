import pytest

from amormortuorum.combat.turn_queue import MinimalActor, TurnQueue


def test_spd_descending_order_and_recalc_each_round():
    a = MinimalActor(id="A", name="A", spd=10, hp=10)
    b = MinimalActor(id="B", name="B", spd=20, hp=10)
    c = MinimalActor(id="C", name="C", spd=15, hp=10)

    tq = TurnQueue([a, b, c], tie_breaker_attr="id")

    first_round = [tq.next_actor().id, tq.next_actor().id, tq.next_actor().id]
    assert first_round == ["B", "C", "A"]

    # Change SPD before the next round starts; should be reflected in next ordering
    a.spd = 25

    second_round = [tq.next_actor().id, tq.next_actor().id, tq.next_actor().id]
    assert second_round == ["A", "B", "C"]


def test_dead_actors_skipped_mid_round_and_excluded_next_round():
    a = MinimalActor(id="A", name="A", spd=20, hp=10)
    b = MinimalActor(id="B", name="B", spd=15, hp=10)
    c = MinimalActor(id="C", name="C", spd=10, hp=10)

    tq = TurnQueue([a, b, c], tie_breaker_attr="id")

    nxt = tq.next_actor()
    assert nxt.id == "A"

    # B dies before their turn
    b.kill()

    nxt2 = tq.next_actor()
    # Should skip B and go to C
    assert nxt2.id == "C"

    # Next round should not include B at all
    round2_first = tq.next_actor()
    assert round2_first.id == "A"
    round2_second = tq.next_actor()
    assert round2_second.id == "C"


def test_ties_are_deterministic_by_id():
    # Same SPD; tiebreaker by id ascending yields deterministic order
    a = MinimalActor(id="2", name="A", spd=10, hp=10)
    b = MinimalActor(id="1", name="B", spd=10, hp=10)

    tq = TurnQueue([a, b], tie_breaker_attr="id")

    order = [tq.next_actor().id, tq.next_actor().id]
    assert order == ["1", "2"]

    # Next round should produce the same deterministic order
    order2 = [tq.next_actor().id, tq.next_actor().id]
    assert order2 == ["1", "2"]


def test_no_alive_actors_returns_none_and_is_stable():
    a = MinimalActor(id="A", name="A", spd=5, hp=0)  # dead
    b = MinimalActor(id="B", name="B", spd=7, hp=0)  # dead

    tq = TurnQueue([a, b])

    assert tq.next_actor() is None
    # Subsequent calls remain None and do not raise
    assert tq.next_actor() is None


def test_adding_and_removing_actors_affects_future_rounds_only():
    a = MinimalActor(id="A", name="A", spd=10, hp=10)
    b = MinimalActor(id="B", name="B", spd=20, hp=10)

    tq = TurnQueue([a, b], tie_breaker_attr="id")

    # Start round 1: order B, A
    assert tq.next_actor().id == "B"

    # Add a new fastest actor mid-round; should not affect the current round
    c = MinimalActor(id="C", name="C", spd=30, hp=10)
    tq.add_actor(c)

    # Still in round 1, next is A
    assert tq.next_actor().id == "A"

    # Round 2 should now include C first
    assert tq.next_actor().id == "C"
    assert tq.next_actor().id == "B"
    assert tq.next_actor().id == "A"

    # Remove B mid-round; they should still be skipped if encountered, but removal
    # affects future rounds
    tq.remove_actor(b)

    # Finish round 3 and ensure B is no longer present
    assert tq.next_actor().id == "C"
    assert tq.next_actor().id == "A"

    # Next round should only have C and A
    assert tq.next_actor().id == "C"
    assert tq.next_actor().id == "A"
