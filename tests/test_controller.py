from types import SimpleNamespace

from amormortuorum.core.controller import ControllerInput, button_to_actions, direction_edges


def test_button_mapping():
    assert button_to_actions("A") == ["confirm"]
    assert button_to_actions("b") == ["cancel"]
    assert button_to_actions("start") == ["pause"]
    assert button_to_actions("y") == ["menu"]
    assert button_to_actions("leftshoulder") == []


def test_direction_edges_fire_once_per_push():
    held, pressed = direction_edges((), 0.0, 1.0)
    assert held == ("move_up",) and pressed == ["move_up"]
    held, pressed = direction_edges(held, 0.1, 0.9)  # still held: no repeat
    assert pressed == []
    held, pressed = direction_edges(held, 0.0, 0.0)  # released
    assert held == () and pressed == []
    held, pressed = direction_edges(held, -1.0, -1.0)  # diagonal pushes both
    assert set(pressed) == {"move_left", "move_down"}
    _, pressed = direction_edges((), 0.3, 0.3)  # inside the dead zone
    assert pressed == []


def test_controller_input_dispatches_actions_from_events():
    received = []
    ci = ControllerInput(lambda actions: received.append(list(actions)))
    pad = SimpleNamespace(name="pad")
    ci._on_button_press(pad, "a")
    ci._on_dpad_motion(pad, SimpleNamespace(x=1.0, y=0.0))
    ci._on_dpad_motion(pad, SimpleNamespace(x=1.0, y=0.0))  # held
    ci._on_stick_motion(pad, "rightstick", SimpleNamespace(x=0.0, y=1.0))  # ignored
    ci._on_stick_motion(pad, "leftstick", SimpleNamespace(x=0.0, y=-1.0))
    assert received == [["confirm"], ["move_right"], ["move_down"]]
    assert ci.connected is None
