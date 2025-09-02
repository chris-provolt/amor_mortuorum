from amor.ui.hud.level_indicator import LevelIndicator


def test_level_indicator_label():
    level = 7
    widget = LevelIndicator(lambda: level)
    assert widget.get_label() == "Lv. 7"
