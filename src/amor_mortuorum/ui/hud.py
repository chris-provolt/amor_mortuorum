from dataclasses import dataclass
from typing import Protocol

from ..economy.events import EventBus, GoldChangedEvent


class GoldHudSink(Protocol):
    """A UI sink that receives gold updates. This abstracts away Arcade UI.

    Implementations could render text in the HUD, for example.
    """

    def update_gold(self, amount: int) -> None:  # pragma: no cover - interface
        ...


@dataclass
class HUDGoldPresenter:
    """Presenter that listens to GoldChangedEvent and updates a HUD sink.

    This keeps UI logic out of the core model and makes it testable.
    """

    bus: EventBus
    sink: GoldHudSink
    _current: int = 0

    def start(self, initial_amount: int) -> None:
        self._current = max(0, int(initial_amount))
        self.sink.update_gold(self._current)
        self.bus.subscribe(GoldChangedEvent, self._on_gold_changed)

    def stop(self) -> None:
        self.bus.unsubscribe(GoldChangedEvent, self._on_gold_changed)

    # Event handler
    def _on_gold_changed(self, evt: GoldChangedEvent) -> None:
        self._current = evt.new_amount
        self.sink.update_gold(self._current)
