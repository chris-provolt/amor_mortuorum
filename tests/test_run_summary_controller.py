from amormortuorum.core.navigation import NextAction
from amormortuorum.domain.run_summary import RunOutcome, RunSummary
from amormortuorum.ui.run_summary_view import RunSummaryController


def make_summary():
    return RunSummary.from_run_stats(
        outcome=RunOutcome.DEATH,
        depth_reached=10,
        enemies_defeated=25,
    )


def test_controller_default_action_goes_to_graveyard():
    c = RunSummaryController(make_summary())
    assert c.default_action() == NextAction.TO_GRAVEYARD


def test_controller_key_mapping_and_callback_invocation():
    chosen = []

    def cb(action):
        chosen.append(action)

    c = RunSummaryController(make_summary(), on_complete=cb)

    # Unknown key -> None
    assert c.handle_key("x") is None
    assert chosen == []

    # Enter -> Graveyard
    act = c.handle_key("enter")
    assert act == NextAction.TO_GRAVEYARD
    assert chosen[-1] == NextAction.TO_GRAVEYARD

    # Space -> Graveyard
    act = c.handle_key("space")
    assert act == NextAction.TO_GRAVEYARD

    # M -> Main menu
    act = c.handle_key("m")
    assert act == NextAction.TO_MAIN_MENU
    assert chosen[-1] == NextAction.TO_MAIN_MENU


def test_summary_lines_provided():
    c = RunSummaryController(make_summary())
    lines = c.summary_lines(width=50)
    assert any("Floors cleared:" in l for l in lines)
