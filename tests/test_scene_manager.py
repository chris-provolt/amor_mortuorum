from amormortuorum.core.scenes.base_scene import BaseScene
from amormortuorum.core.scenes.manager import SceneManager


class DummyWindow:
    width = 800
    height = 600


class StubScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.entered = False
        self.exited = False
        self.paused = 0
        self.resumed = 0
        self.updated = 0
        self.drawn = 0
        self.resized = []
        self.actions_handled = []

    def on_enter(self):
        self.entered = True

    def on_exit(self):
        self.exited = True

    def on_pause(self):
        self.paused += 1

    def on_resume(self):
        self.resumed += 1

    def on_resize(self, width, height):
        self.resized.append((width, height))

    def update(self, delta_time: float):
        self.updated += 1

    def draw(self):
        self.drawn += 1

    def on_key_actions(self, actions, pressed: bool):
        self.actions_handled.append((tuple(actions), pressed))
        return True


class OtherScene(StubScene):
    pass


def test_push_pop_replace_and_delegation():
    mgr = SceneManager(DummyWindow())
    s1 = StubScene(DummyWindow())
    s2 = StubScene(DummyWindow())

    mgr.push(s1)
    assert mgr.current is s1
    assert s1.entered is True

    mgr.update(0.016)
    mgr.draw()
    assert s1.updated == 1
    assert s1.drawn == 1

    # Replace with s2
    mgr.replace(s2)
    assert s1.exited is True
    assert mgr.current is s2
    assert s2.entered is True

    # Input delegation should go to s2 and be handled
    handled = mgr.key_actions(["confirm"], pressed=True)
    assert handled is True

    # Pop should remove s2
    popped = mgr.pop()
    assert popped is s2
    assert mgr.current is None


def test_push_pauses_and_pop_resumes_underlying_scene():
    mgr = SceneManager(DummyWindow())
    below = StubScene(DummyWindow())
    above = StubScene(DummyWindow())

    mgr.push(below)
    mgr.push(above)
    assert below.paused == 1
    assert below.resumed == 0
    assert mgr.current is above

    # Only the top scene updates and draws
    mgr.update(0.016)
    assert above.updated == 1
    assert below.updated == 0

    mgr.pop()
    assert below.resumed == 1
    assert above.exited is True
    assert mgr.current is below


def test_pop_until_unwinds_to_scene_type():
    mgr = SceneManager(DummyWindow())
    root = OtherScene(DummyWindow())
    mid = StubScene(DummyWindow())
    top = StubScene(DummyWindow())
    for s in (root, mid, top):
        mgr.push(s)

    result = mgr.pop_until(OtherScene)
    assert result is root
    assert mgr.current is root
    assert len(mgr) == 1
    assert mid.exited and top.exited
    assert root.resumed == 1
    assert mid.manager is None and top.manager is None

    # Unknown type empties the stack and returns None
    assert mgr.pop_until(type("Missing", (BaseScene,), {})) is None
    assert mgr.current is None


def test_resize_reaches_every_stacked_scene():
    mgr = SceneManager(DummyWindow())
    a = StubScene(DummyWindow())
    b = StubScene(DummyWindow())
    mgr.push(a)
    mgr.push(b)
    mgr.resize(1024, 768)
    assert a.resized == [(1024, 768)]
    assert b.resized == [(1024, 768)]
