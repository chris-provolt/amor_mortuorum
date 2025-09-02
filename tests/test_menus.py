import pytest

from ui.menus import VerticalMenu, MenuItem


def test_vertical_menu_navigation_and_select_wraps():
    items = [
        MenuItem("a", "A"),
        MenuItem("b", "B"),
        MenuItem("c", "C"),
    ]
    menu = VerticalMenu(items, wrap_navigation=True)

    # Initial selection is first item
    assert menu.selected_item.id == "a"

    # Up from first wraps to last
    menu.input("up")
    assert menu.selected_item.id == "c"

    # Down moves to first again
    menu.input("down")
    assert menu.selected_item.id == "a"

    # Down to second
    menu.input("down")
    assert menu.selected_item.id == "b"

    # Select returns the current item
    selected = menu.input("select")
    assert selected is not None
    assert selected.id == "b"


def test_vertical_menu_skips_disabled_items():
    items = [
        MenuItem("a", "A", enabled=True),
        MenuItem("b", "B", enabled=False),
        MenuItem("c", "C", enabled=True),
    ]
    menu = VerticalMenu(items, wrap_navigation=True)

    # From A, going down should skip disabled B and land on C
    menu.input("down")
    assert menu.selected_item.id == "c"

    # From C, going up should skip disabled B and land on A
    menu.input("up")
    assert menu.selected_item.id == "a"
