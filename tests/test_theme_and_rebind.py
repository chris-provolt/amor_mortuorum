import arcade

from amormortuorum.core.input import InputManager
from amormortuorum.ui.theme import MAX_SCALE, MIN_SCALE, fs, set_ui_scale, ui_scale


class DummyWindow:
    width = 800
    height = 600


def test_ui_scale_clamps_and_scales_sizes():
    try:
        assert set_ui_scale(1.0) == 1.0
        assert fs(20) == 20
        assert set_ui_scale(5.0) == MAX_SCALE
        assert fs(20) == round(20 * MAX_SCALE)
        assert set_ui_scale(0.1) == MIN_SCALE
        assert fs(10) == max(6, round(10 * MIN_SCALE))
        assert ui_scale() == MIN_SCALE
    finally:
        set_ui_scale(1.0)


def test_rebind_key_moves_key_between_actions():
    im = InputManager(DummyWindow(), mapping={"confirm": ["ENTER"], "cancel": ["ESCAPE", "X"]})
    assert im.key_name(arcade.key.X) == "X"
    assert im.rebind_key("confirm", arcade.key.X) == "X"
    assert im.actions_for_key(arcade.key.X) == ["confirm"]
    assert im.actions_for_key(arcade.key.ENTER) == []  # single-key rebind replaces the set
    names = im.mapping_names()
    assert names["confirm"] == ["X"] and names["cancel"] == ["ESCAPE"]
