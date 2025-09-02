from amor_mortuorum.input import GameController


def test_controller_stub_instantiation_and_methods():
    ctrl = GameController()

    # connect() should succeed in stub
    assert ctrl.connect() is True
    assert ctrl.is_connected is True

    # update() should be callable without error
    ctrl.update()

    # Should start with no events
    assert ctrl.get_events() == []

    # Queue a synthetic button event and fetch it
    ctrl.queue_button_event("DPAD_UP", pressed=True)
    events = ctrl.get_events()
    assert len(events) == 1
    assert events[0].pressed is True

    ctrl.disconnect()
    assert ctrl.is_connected is False
