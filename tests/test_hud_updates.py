import pytest

from amormortuorum.state import GameSession, PlayerStats
from amormortuorum.ui import HUD


def test_hud_initial_values_reflect_state():
    session = GameSession(start_floor=3, minimap_visible=True)
    player = PlayerStats(max_hp=100, hp=75, max_mp=40, mp=28, gold=123)

    hud = HUD(session, player)
    data = hud.get_display_data()

    assert data["hp"] == "75/100"
    assert data["mp"] == "28/40"
    assert data["gold"] == 123
    assert data["floor"] == 3
    assert data["minimap_visible"] is True


def test_hud_updates_live_on_player_change():
    session = GameSession(start_floor=10)
    player = PlayerStats(max_hp=200, hp=200, max_mp=50, mp=10, gold=0)

    hud = HUD(session, player)

    # Change HP and Gold; HUD should update via listener
    player.change_hp(-37)
    player.add_gold(77)

    data = hud.get_display_data()
    assert data["hp"] == "163/200"
    assert data["gold"] == 77

    # Change MP and clamp behavior
    player.change_mp(1000)  # exceeds max
    data = hud.get_display_data()
    assert data["mp"] == "50/50"


def test_hud_updates_on_session_change():
    session = GameSession(start_floor=1, minimap_visible=False)
    player = PlayerStats()
    hud = HUD(session, player)

    session.set_floor(15)
    hud.notify_session_changed()  # session does not auto-notify; call from controller/view
    data = hud.get_display_data()

    assert data["floor"] == 15

    session.toggle_minimap()
    hud.notify_session_changed()
    data = hud.get_display_data()
    assert data["minimap_visible"] is True
