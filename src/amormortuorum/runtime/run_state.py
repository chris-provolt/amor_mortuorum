import logging
from dataclasses import dataclass, field
from typing import Optional

from amormortuorum.utils.events import EventBus

logger = logging.getLogger(__name__)


@dataclass
class RunState:
    """Tracks the current run and emits events on run lifecycle changes.

    The Shop subscribes to 'run_started' to reset stock.
    """

    events: EventBus = field(default_factory=EventBus)
    run_id: Optional[int] = None

    def start_new_run(self) -> int:
        """Start a new run, incrementing run_id and notifying subscribers."""
        if self.run_id is None:
            self.run_id = 1
        else:
            self.run_id += 1
        logger.info("Starting new run: %s", self.run_id)
        self.events.publish("run_started", {"run_id": self.run_id})
        return self.run_id
