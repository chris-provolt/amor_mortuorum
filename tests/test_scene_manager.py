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
        self.updated = 0
        self.drawn = 0
        self.actions_handled = []

    def on_enter(self):
        self.entered = True

    def on_exit(self):
        self.exited = True

    def update(self, delta_time: float):
        self.updated += 1

    def draw(self):
        self.drawn += 1

    def on_key_actions(self, actions, pressed: bool):
        self.actions_handled.append((tuple(actions), pressed))
        return True


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
