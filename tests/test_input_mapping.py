import pytest

from amor_mortuorum.input import InputAction, InputMapper


def test_default_mapping_movement_arrows_and_wasd():
    mapper = InputMapper.default()

    # Up
    assert mapper.translate_key("UP") == InputAction.MOVE_UP
    assert mapper.translate_key("W") == InputAction.MOVE_UP
    # Case-insensitive
    assert mapper.translate_key("w") == InputAction.MOVE_UP

    # Down
    assert mapper.translate_key("DOWN") == InputAction.MOVE_DOWN
    assert mapper.translate_key("S") == InputAction.MOVE_DOWN

    # Left
    assert mapper.translate_key("LEFT") == InputAction.MOVE_LEFT
    assert mapper.translate_key("A") == InputAction.MOVE_LEFT

    # Right
    assert mapper.translate_key("RIGHT") == InputAction.MOVE_RIGHT
    assert mapper.translate_key("D") == InputAction.MOVE_RIGHT


def test_default_mapping_confirm_and_back():
    mapper = InputMapper.default()

    # Confirm
    assert mapper.translate_key("ENTER") == InputAction.CONFIRM
    assert mapper.translate_key("RETURN") == InputAction.CONFIRM
    assert mapper.translate_key("ret") == InputAction.CONFIRM  # via alias to ENTER

    # Back
    assert mapper.translate_key("ESCAPE") == InputAction.BACK
    assert mapper.translate_key("ESC") == InputAction.BACK
    assert mapper.translate_key("eSc") == InputAction.BACK


def test_on_key_event_helper_creates_events():
    mapper = InputMapper.default()

    event = mapper.on_key_event("w", pressed=True)
    assert event is not None
    assert event.action == InputAction.MOVE_UP
    assert event.pressed is True
    assert event.source == "keyboard"

    # Unbound key returns None
    assert mapper.on_key_event("F13", pressed=True) is None


def test_rebinding_changes_behavior():
    mapper = InputMapper.default()

    # Rebind A from left to confirm, for example
    mapper.bind("A", InputAction.CONFIRM)
    assert mapper.translate_key("A") == InputAction.CONFIRM

    # Unbind and verify None
    mapper.unbind("A")
    assert mapper.translate_key("A") == None


def test_alias_registration_for_numeric_keys():
    mapper = InputMapper.default()

    # Suppose a backend uses 1234 to mean ENTER; alias then translate
    mapper.set_alias(1234, "ENTER")
    assert mapper.translate_key(1234) == InputAction.CONFIRM
