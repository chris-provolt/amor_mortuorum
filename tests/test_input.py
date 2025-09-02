import arcade

from amormortuorum.core.input import InputManager


class DummyWindow:
    width = 800
    height = 600


def test_default_mapping_contains_expected_actions():
    im = InputManager(DummyWindow(), mapping=None)
    # W or UP maps to move_up
    actions_w = im.actions_for_key(arcade.key.W)
    actions_up = im.actions_for_key(arcade.key.UP)
    assert "move_up" in actions_w
    assert "move_up" in actions_up
    # Enter maps to confirm
    assert "confirm" in im.actions_for_key(arcade.key.ENTER)


def test_binding_and_press_release_flow():
    im = InputManager(DummyWindow(), mapping={"pause": ["P"]})
    # Initially only pause
    assert im.actions_for_key(arcade.key.P) == ["pause"]
    # Bind confirm -> SPACE
    im.bind("confirm", ["SPACE"])
    assert set(im.actions_for_key(arcade.key.SPACE)) == {"confirm"}
    # Simulate press/release
    actions = im.process_key_press(arcade.key.SPACE, modifiers=0)
    assert actions == ["confirm"]
    assert im.is_pressed("confirm") is True
    actions = im.process_key_release(arcade.key.SPACE, modifiers=0)
    assert actions == ["confirm"]
    assert im.is_pressed("confirm") is False
