import time

from amor_mortuorum.combat.log import CombatLog, PagedLogViewModel


def test_add_events_and_pagination():
    log = CombatLog(capacity=50)
    log.start_new_battle()

    # Add 23 events
    for i in range(1, 24):
        log.add_event(
            turn_index=i,
            actor=f"Hero",
            action="Attack",
            target="Slime",
            value=5 + i,
            tags=["damage"],
        )

    vm = PagedLogViewModel(log, page_size=10)

    # Default not in history mode, should show last page (3 pages total => index 2) with last 3 entries
    assert vm.total_pages == 3
    assert vm.page_index == vm.last_page_index == 2
    lines = vm.get_page_lines()
    assert len(lines) == 3
    assert "Hero uses Attack" in lines[-1]

    # Enter history mode and navigate
    vm.toggle_history_mode()
    assert vm.page_index == 2
    vm.prev_page()
    assert vm.page_index == 1
    vm.prev_page()
    assert vm.page_index == 0
    vm.prev_page()  # should clamp
    assert vm.page_index == 0

    # Go next
    vm.next_page()
    assert vm.page_index == 1


def test_log_capacity_and_recent():
    log = CombatLog(capacity=5)
    log.start_new_battle()
    for i in range(10):
        log.add_event(turn_index=i + 1, actor="H", action="Ping", value=i, tags=["info"])  # type: ignore[arg-type]

    # Capacity enforced
    assert len(log) == 5
    rec = log.get_recent(3)
    assert [e.value for e in rec] == [7, 8, 9]


def test_log_serialization_roundtrip():
    log = CombatLog(capacity=10)
    log.start_new_battle()
    e = log.add_event(turn_index=1, actor="Mage", action="Heal", target="Mage", value=12, tags=["heal"])
    data = log.to_dict()

    loaded = CombatLog.from_dict(data)
    assert len(loaded) == 1
    ev = loaded.events()[0]
    assert ev.message == e.message
    assert ev.actor == "Mage"


def test_history_mode_toggle():
    log = CombatLog()
    log.start_new_battle()
    for i in range(15):
        log.add_event(turn_index=i + 1, actor="A", action="X", tags=["info"])  # type: ignore[arg-type]
    vm = PagedLogViewModel(log, page_size=5)

    # Not in history -> always last
    assert vm.page_index == vm.last_page_index
    vm.toggle_history_mode()
    assert vm.history_mode is True
    vm.go_to_first()
    assert vm.page_index == 0
    vm.toggle_history_mode()  # exit history -> snap to last
    assert vm.history_mode is False
    assert vm.page_index == vm.last_page_index
