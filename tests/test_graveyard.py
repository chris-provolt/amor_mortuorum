import types
import sys

import pytest


class ArcadeStub(types.SimpleNamespace):
    def __init__(self):
        super().__init__()
        # Key constants
        key = types.SimpleNamespace(
            UP=1,
            DOWN=2,
            W=3,
            S=4,
            ENTER=5,
            RETURN=6,
            SPACE=7,
        )
        self.key = key

        # View base class
        class View:
            def __init__(self):
                self.window = None

            def on_show_view(self):
                pass

            def on_draw(self):
                pass

        self.View = View

        # Render helpers (no-op)
        def start_render():
            return None

        def draw_text(*args, **kwargs):
            return None

        def set_background_color(*args, **kwargs):
            return None

        self.start_render = start_render
        self.draw_text = draw_text
        self.set_background_color = set_background_color


@pytest.fixture(autouse=True)
def stub_arcade(monkeypatch):
    # Provide a stub 'arcade' module before importing scenes
    stub = ArcadeStub()
    sys.modules['arcade'] = stub
    yield
    # Cleanup
    sys.modules.pop('arcade', None)


def test_graveyard_enter_transitions_to_dungeon(monkeypatch):
    # Import after stubbing arcade
    from scenes.graveyard import GraveyardView
    from scenes.dungeon import DungeonView

    class FakeWindow:
        def __init__(self):
            self.last_view = None

        def show_view(self, view):
            self.last_view = view

        def close(self):
            pass

    view = GraveyardView()
    win = FakeWindow()
    view.window = win

    # Press ENTER while 'Enter' is the default selected item
    import arcade as arcade_mod
    view.on_key_press(arcade_mod.key.ENTER, 0)

    assert isinstance(win.last_view, DungeonView)
    assert getattr(win.last_view, 'start_floor', None) == 1


def test_graveyard_navigation_changes_selection(monkeypatch):
    from scenes.graveyard import GraveyardView
    import arcade as arcade_mod

    view = GraveyardView()

    # Initially 'Enter'
    assert view.menu.selected_item.label == 'Enter'

    # Move down to 'Rest'
    view.on_key_press(arcade_mod.key.DOWN, 0)
    assert view.menu.selected_item.label == 'Rest'

    # Move down to 'Crypt'
    view.on_key_press(arcade_mod.key.DOWN, 0)
    assert view.menu.selected_item.label == 'Crypt'
