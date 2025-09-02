from amormortuorum.state import GameSession
from amormortuorum.ui import Minimap
from amormortuorum.input import KeyboardController
from amormortuorum.config import KEY_MINIMAP_TOGGLE


def test_minimap_toggle_persists_in_session():
    session = GameSession(start_floor=5, minimap_visible=True)
    minimap = Minimap(session)

    assert minimap.visible is True

    # Toggle with controller
    controller = KeyboardController(minimap)
    handled = controller.handle_key_press(KEY_MINIMAP_TOGGLE)
    assert handled is True
    assert minimap.visible is False
    assert session.minimap_visible is False

    # Create a fresh Minimap with the same session to validate persistence
    minimap2 = Minimap(session)
    assert minimap2.visible is False

    # Toggle again using arcade-like key code path
    handled = controller.handle_key_press(ord(KEY_MINIMAP_TOGGLE))
    assert handled is True
    assert minimap2.visible is True


def test_keyboard_controller_unhandled_keys():
    session = GameSession()
    minimap = Minimap(session)
    controller = KeyboardController(minimap)

    # Unmapped key should not change state
    before = minimap.visible
    handled = controller.handle_key_press("Z")
    assert handled is False
    assert minimap.visible == before
