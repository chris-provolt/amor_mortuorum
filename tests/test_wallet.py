import pytest

from amor_mortuorum.economy.events import EventBus, GoldChangedEvent
from amor_mortuorum.economy.wallet import GoldWallet


def test_wallet_add_and_spend_and_events():
    bus = EventBus()
    wallet = GoldWallet(event_bus=bus)

    events = []

    def handler(evt: GoldChangedEvent):
        events.append(evt)

    bus.subscribe(GoldChangedEvent, handler)

    added = wallet.add(50, reason="grant")
    assert added == 50
    assert wallet.amount == 50

    spent = wallet.spend(20, reason="purchase")
    assert spent == 20
    assert wallet.amount == 30

    assert len(events) == 2
    assert events[0].old_amount == 0 and events[0].new_amount == 50 and events[0].delta == 50 and events[0].reason == "grant"
    assert events[1].old_amount == 50 and events[1].new_amount == 30 and events[1].delta == -20 and events[1].reason == "purchase"

    with pytest.raises(ValueError):
        wallet.spend(100)

    with pytest.raises(ValueError):
        wallet.add(-1)
