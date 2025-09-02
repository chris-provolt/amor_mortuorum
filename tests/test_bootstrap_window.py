import sys
import types

import importlib


class _StubArcadeWindow:
    def __init__(self, width, height, title, resizable=True, **kwargs):
        self.width = width
        self.height = height
        self.title = title
        self.resizable = resizable
        self.kwargs = kwargs

    # Simulate arcade.Window behavior
    def on_resize(self, width, height):  # called by subclass via super()
        self.width = width
        self.height = height

    def clear(self):
        # No-op for tests
        pass


class _StubArcadeModule(types.ModuleType):
    def __init__(self):
        super().__init__("arcade")
        self.Window = _StubArcadeWindow
        self._last_background_color = None
        self._last_viewport = None
        self._run_called = False

    # API used by our code
    def set_background_color(self, color):
        self._last_background_color = color

    def set_viewport(self, left, right, bottom, top):
        self._last_viewport = (left, right, bottom, top)

    def run(self):
        self._run_called = True


def with_stub_arcade():
    """Context manager-like helper to inject the stub arcade module."""
    stub = _StubArcadeModule()
    sys.modules["arcade"] = stub
    return stub


def test_create_window_sets_title_resizable_and_background_color(monkeypatch):
    stub_arcade = with_stub_arcade()

    # Import after injecting stub
    game_main = importlib.import_module("game.main")

    window = game_main.create_window(width=800, height=600)

    assert isinstance(window, stub_arcade.Window)
    assert window.title == "Amor Mortuorum"
    assert window.resizable is True
    # Background color is set globally via arcade.set_background_color
    assert stub_arcade._last_background_color == game_main.BASE_BG_COLOR


def test_on_resize_updates_viewport(monkeypatch):
    stub_arcade = with_stub_arcade()

    game_main = importlib.import_module("game.main")
    window = game_main.create_window(width=400, height=300)

    # Call the resize handler and verify viewport mapping
    window.on_resize(1024, 768)
    assert stub_arcade._last_viewport == (0, 1024, 0, 768)


def test_module_entrypoint_runs_app_loop(monkeypatch):
    stub_arcade = with_stub_arcade()

    # Re-import main to bind to the stubbed arcade
    importlib.invalidate_caches()
    game_main = importlib.import_module("game.main")

    # Import __main__ and run main()
    game_dunder_main = importlib.import_module("game.__main__")

    # Call the main function directly to avoid actually exiting the test
    exit_code = game_main.main([])

    assert exit_code == 0
    assert stub_arcade._run_called is True
