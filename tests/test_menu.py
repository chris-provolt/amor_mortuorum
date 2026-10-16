from amormortuorum.ui.menu import MenuItem, VerticalMenu


def test_move_wraps_and_skips_disabled():
    fired = []
    menu = VerticalMenu(
        [
            MenuItem("A", lambda: fired.append("A")),
            MenuItem("B", enabled=False),
            MenuItem("C", lambda: fired.append("C")),
        ]
    )
    assert menu.current.label == "A"
    menu.move(+1)
    assert menu.current.label == "C"  # skipped B
    menu.move(+1)
    assert menu.current.label == "A"  # wrapped
    menu.move(-1)
    assert menu.current.label == "C"
    assert menu.activate() is True
    assert fired == ["C"]


def test_no_wrap_stops_at_edges():
    menu = VerticalMenu([MenuItem("A"), MenuItem("B")], wrap=False)
    menu.move(-1)
    assert menu.selected == 0
    menu.move(+5)
    assert menu.selected == 1


def test_initial_cursor_snaps_past_disabled_first_item():
    menu = VerticalMenu([MenuItem("A", enabled=False), MenuItem("B")])
    assert menu.current.label == "B"
    assert VerticalMenu([]).current is None
    assert VerticalMenu([]).activate() is False


def test_handle_actions_maps_inputs():
    hits = []
    menu = VerticalMenu(
        [MenuItem("A", lambda: hits.append(1)), MenuItem("B", lambda: hits.append(2))]
    )
    assert menu.handle_actions(["move_down"]) is True
    assert menu.current.label == "B"
    assert menu.handle_actions(["confirm"]) is True
    assert hits == [2]
    assert menu.handle_actions(["cancel"]) is False


def test_set_items_keeps_selection_in_range():
    menu = VerticalMenu([MenuItem("A"), MenuItem("B"), MenuItem("C")])
    menu.move(+2)
    menu.set_items([MenuItem("X"), MenuItem("Y")])
    assert menu.selected == 1
    menu.set_items([MenuItem("Only", enabled=False)])
    assert menu.activate() is False


def test_combat_flash_fades_linearly_to_zero():
    from amormortuorum.scenes.combat import FLASH_ALPHA, FLASH_TIME, flash_alpha

    assert flash_alpha(FLASH_TIME) == FLASH_ALPHA
    assert flash_alpha(FLASH_TIME / 2) == round(FLASH_ALPHA / 2)
    assert flash_alpha(0.0) == 0 and flash_alpha(-1.0) == 0
    assert flash_alpha(FLASH_TIME * 3) == FLASH_ALPHA  # never brighter than the peak


def test_lunge_offset_dashes_in_and_returns():
    from amormortuorum.scenes.combat import IMPACT_AT, LUNGE_PX, lunge_offset

    assert lunge_offset(0.0) == 0.0
    assert abs(lunge_offset(IMPACT_AT) - LUNGE_PX) < 1e-6  # the blow lands at full reach
    assert 0 < lunge_offset(IMPACT_AT / 2) < LUNGE_PX
    assert abs(lunge_offset(1.0)) < 1e-6
    assert lunge_offset(-1) == 0.0 and abs(lunge_offset(2.0)) < 1e-6


def test_menu_items_may_carry_an_icon():
    from amormortuorum.ui.menu import MenuItem, VerticalMenu

    menu = VerticalMenu([MenuItem("Potion", icon="icon_potion"), MenuItem("Back")])
    assert menu.items[0].icon == "icon_potion" and menu.items[1].icon is None
