from amormortuorum.combat.actions import Command
from amormortuorum.combat.command_menu import CommandMenu, MenuState, Target


def test_menu_navigation_wraps():
    menu = CommandMenu()
    assert menu.index == 0

    # Move up from first should wrap to last
    menu.move_up()
    assert menu.index == len(menu.options) - 1

    # Move down should wrap back to first
    menu.move_down()
    assert menu.index == 0


def test_attack_requires_target_transitions_to_target_select():
    menu = CommandMenu()
    # Ensure ATTACK is current option index 0 by default
    assert menu.current_option == Command.ATTACK

    # Provide targets and confirm
    targets = [Target(id="t1", name="Goblin"), Target(id="t2", name="Orc")]
    res = menu.confirm(targets=targets)
    assert res is None
    assert menu.state == MenuState.TARGET_SELECT
    # Target list should be filtered to alive only (all alive)
    assert len(menu.targets) == 2
    assert menu.target_index == 0


def test_confirm_target_completes_selection():
    menu = CommandMenu()
    targets = [Target(id="t1", name="Goblin"), Target(id="t2", name="Orc")]
    menu.confirm(targets=targets)  # Transition to target select

    # Move right to second target
    menu.move_right()
    assert menu.target_index == 1

    result = menu.confirm()
    assert result is not None
    assert result.command == Command.ATTACK
    assert result.target_id == "t2"
    assert menu.state == MenuState.COMPLETE


def test_cancel_returns_to_menu_from_target_select():
    menu = CommandMenu()
    targets = [Target(id="t1", name="Goblin")]
    menu.confirm(targets=targets)
    assert menu.state == MenuState.TARGET_SELECT

    cancelled = menu.cancel()
    assert cancelled is True
    assert menu.state == MenuState.MENU
    assert menu.selected_command is None


def test_non_target_commands_complete_immediately():
    menu = CommandMenu()
    # Move to FLEE option
    while menu.current_option != Command.FLEE:
        menu.move_down()

    res = menu.confirm()
    assert res is not None
    assert res.command == Command.FLEE
    assert res.target_id is None
    assert menu.state == MenuState.COMPLETE


def test_no_targets_raises_value_error():
    menu = CommandMenu()
    # ATTACK is selected; no targets provided
    try:
        menu.confirm(targets=[])
        assert False, "Expected ValueError when confirming with no targets"
    except ValueError:
        assert True


def test_dead_targets_are_filtered_out():
    menu = CommandMenu()
    targets = [
        Target(id="t1", name="Goblin", alive=False),
        Target(id="t2", name="Orc", alive=True),
    ]
    menu.confirm(targets=targets)
    assert menu.state == MenuState.TARGET_SELECT
    # Only alive target remains
    assert len(menu.targets) == 1
    assert menu.targets[0].id == "t2"
