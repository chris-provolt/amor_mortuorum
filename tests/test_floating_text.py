from typing import List, Tuple

from amor_mortuorum.ui.floating_text import FloatingCombatText, FloatingTextManager, TextRenderer


class DummyRenderer(TextRenderer):
    def __init__(self) -> None:
        self.calls: List[Tuple[str, float, float, tuple, int, bool, str]] = []

    def draw_text(self, text: str, x: float, y: float, color, font_size: int = 12, bold: bool = False, anchor_x: str = "center") -> None:
        self.calls.append((text, x, y, color, font_size, bold, anchor_x))


def test_floating_text_lifecycle():
    fct = FloatingCombatText(text="-12", color=(235, 64, 52, 255), duration=1.0, x=0, y=0, vy=50, gravity=-100)

    # Initially not expired and alpha should be increasing
    r = DummyRenderer()
    for i in range(5):
        fct.update(0.1)
        fct.draw(r)
        assert fct.expired is False
    assert len(r.calls) == 5

    # Advance time to expire
    fct.update(1.0)
    assert fct.expired is True


def test_floating_text_anchor_follow():
    # Anchor lookup returns moving target
    target_pos = {"t1": (100.0, 200.0)}

    def lookup(anchor_id: str):
        return target_pos[anchor_id]

    fct = FloatingCombatText(text="+8", color=(64, 220, 120, 255), duration=1.0, x=0, y=20, anchor_id="t1")

    r = DummyRenderer()
    fct.update(0.1, lookup)
    fct.draw(r)
    assert r.calls[-1][1] == fct.render_x
    assert r.calls[-1][2] == fct.render_y

    # Move the anchor and update; ensure text follows
    target_pos["t1"] = (120.0, 210.0)
    fct.update(0.1, lookup)
    fct.draw(r)
    assert r.calls[-1][1] == fct.render_x
    assert r.calls[-1][2] == fct.render_y


def test_manager_add_effects_and_draw():
    mgr = FloatingTextManager(max_texts=2)
    r = DummyRenderer()

    # Add two texts
    mgr.add_effect(anchor_id=None, text="-15", kind="damage", base_position=(10, 10))
    mgr.add_effect(anchor_id=None, text="Miss", kind="miss", base_position=(20, 20))

    # Adding a third should drop the oldest due to max_texts=2
    mgr.add_effect(anchor_id=None, text="+7", kind="heal", base_position=(30, 30))
    assert mgr.active_count() == 2

    # Update and draw
    mgr.update(0.16)
    mgr.draw(r)
    assert len(r.calls) == 2
