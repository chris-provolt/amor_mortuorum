from typing import List

from amor_mortuorum.economy.events import EventBus
from amor_mortuorum.economy.wallet import GoldWallet
from amor_mortuorum.ui.hud import HUDGoldPresenter, GoldHudSink


class DummySink(GoldHudSink):
    def __init__(self) -> None:
        self.values: List[int] = []

    def update_gold(self, amount: int) -> None:
        self.values.append(amount)


def test_hud_receives_gold_updates():
    bus = EventBus()
    wallet = GoldWallet(event_bus=bus)
    sink = DummySink()
    presenter = HUDGoldPresenter(bus=bus, sink=sink)

    presenter.start(initial_amount=wallet.amount)

    wallet.add(10, reason="grant")
    wallet.spend(3, reason="purchase")

    # Sequence: initial push, add, spend
    assert sink.values == [0, 10, 7]

    presenter.stop()
