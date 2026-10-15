from amormortuorum.systems.rng import chest_rng, floor_rng, stream_rng


def _draw(rng, n=10):
    return [rng.random() for _ in range(n)]


def test_floor_rng_is_deterministic_and_floor_specific():
    assert _draw(floor_rng(7, 3)) == _draw(floor_rng(7, 3))
    assert _draw(floor_rng(7, 3)) != _draw(floor_rng(7, 4))
    assert _draw(floor_rng(7, 3)) != _draw(floor_rng(8, 3))


def test_chest_rng_differs_from_floor_rng():
    assert _draw(chest_rng(7, 3)) != _draw(floor_rng(7, 3))
    assert _draw(chest_rng(7, 3)) == _draw(chest_rng(7, 3))


def test_named_streams_are_independent():
    assert _draw(stream_rng(1, 1, "encounters")) == _draw(stream_rng(1, 1, "encounters"))
    assert _draw(stream_rng(1, 1, "encounters")) != _draw(stream_rng(1, 1, "combat"))
    assert _draw(stream_rng(1, 1, "combat")) != _draw(stream_rng(1, 2, "combat"))
