import os
import types

# Ensure pyglet/arcade operate in headless mode during tests
os.environ.setdefault("PYGLET_HEADLESS", "true")

import builtins
import importlib
import sys
import pytest

# Ensure src/ is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class MockWindow:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height


class FakeCamera:
    def __init__(self, width, height):
        self.created_with = (int(width), int(height))
        self._size = (int(width), int(height))
        self.resized_to = []

    def resize(self, width, height):
        self._size = (int(width), int(height))
        self.resized_to.append(self._size)

    def use(self):
        # No-op for tests
        pass


@pytest.fixture(autouse=True)
def isolate_arcade(monkeypatch):
    """Monkeypatch arcade functions used by SceneBase to avoid GL usage and to observe calls."""
    import arcade

    # Intercept set_viewport to capture last values
    calls = {"set_viewport": []}

    def fake_set_viewport(left, right, bottom, top):
        calls["set_viewport"].append((left, right, bottom, top))

    # Intercept draw_text so that calling draw_centered_text won't require a GL context
    def fake_draw_text(*args, **kwargs):
        calls.setdefault("draw_text", []).append((args, kwargs))

    monkeypatch.setattr(arcade, "set_viewport", fake_set_viewport)
    monkeypatch.setattr(arcade, "draw_text", fake_draw_text)
    # Replace Camera class with our fake, but do it on the module under test for reliability
    # We'll apply this in a later fixture after importing the module.

    yield calls


@pytest.fixture
def scene_base_module(monkeypatch):
    # Import the module, then replace its arcade.Camera with our FakeCamera
    import core.scene_base as scene_base
    monkeypatch.setattr(scene_base.arcade, "Camera", FakeCamera)
    return scene_base


def test_on_show_view_applies_viewport_and_creates_cameras(isolate_arcade, scene_base_module):
    SceneBase = scene_base_module.SceneBase
    view = SceneBase()
    view.window = MockWindow(1280, 720)

    view.on_show_view()

    # Cameras should be created
    assert view.world_camera is not None
    assert view.ui_camera is not None

    # Viewport should be applied to window size
    assert isolate_arcade["set_viewport"], "set_viewport must be called"
    left, right, bottom, top = isolate_arcade["set_viewport"][-1]
    assert (left, right, bottom, top) == (0, 1280, 0, 720)


def test_on_resize_updates_cameras_and_viewport(isolate_arcade, scene_base_module):
    SceneBase = scene_base_module.SceneBase
    view = SceneBase()
    view.window = MockWindow(800, 600)

    # Initialize via on_show_view (creates cameras using initial size)
    view.on_show_view()

    # Resize window
    view.window.width = 1024
    view.window.height = 768

    view.on_resize(1024, 768)

    # Our FakeCamera tracks resize calls
    assert isinstance(view.world_camera, FakeCamera)
    assert isinstance(view.ui_camera, FakeCamera)

    assert view.world_camera.resized_to[-1] == (1024, 768)
    assert view.ui_camera.resized_to[-1] == (1024, 768)

    # And viewport should be reapplied
    assert isolate_arcade["set_viewport"], "set_viewport must be called"
    left, right, bottom, top = isolate_arcade["set_viewport"][-1]
    assert (left, right, bottom, top) == (0, 1024, 0, 768)


def test_draw_centered_text_uses_window_center(isolate_arcade, scene_base_module):
    SceneBase = scene_base_module.SceneBase
    view = SceneBase()
    view.window = MockWindow(1920, 1080)

    # Ensure cameras created to mimic normal flow
    view.on_show_view()

    # Activate UI camera (no-op fake)
    view.use_ui()

    # Draw centered text; with our fake draw_text, this shouldn't require GL
    view.draw_centered_text("Hello")

    assert "draw_text" in isolate_arcade
    args, kwargs = isolate_arcade["draw_text"][-1]

    # Args: (text, x, y, ...); text should match, x and y should be center
    assert args[0] == "Hello"
    assert pytest.approx(args[1]) == 960  # center_x
    assert pytest.approx(args[2]) == 540  # center_y

    # Anchors should be center/center
    assert kwargs.get("anchor_x") == "center"
    assert kwargs.get("anchor_y") == "center"
