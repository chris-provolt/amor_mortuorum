from __future__ import annotations

import logging
from typing import Optional

from ...core.events import EventBus
from ...meta.relics_manager import RelicsManager, RelicsSnapshot

logger = logging.getLogger(__name__)


class GraveyardRelicsPanel:
    """A UI panel for the Graveyard that shows Relics collection progress.

    This implementation is renderer-agnostic and simply maintains a text string.
    In the actual game, integrate with Arcade to draw this text or icons.
    """

    def __init__(self, manager: RelicsManager, bus: EventBus) -> None:
        self._manager = manager
        self._bus = bus
        self._text: str = ""
        self._bus.subscribe(RelicsManager.EVENT_UPDATED, self._on_relics_updated)
        # Initialize text from current state
        self._refresh_text()

    @property
    def text(self) -> str:
        return self._text

    def _on_relics_updated(self, snapshot: Optional[RelicsSnapshot]) -> None:
        logger.debug("RelicsPanel received update: %r", snapshot)
        self._refresh_text(snapshot)

    def _refresh_text(self, snapshot: Optional[RelicsSnapshot] = None) -> None:
        if snapshot is None:
            c, t, f = self._manager.progress()
        else:
            c, t, f = snapshot.collected_count, snapshot.total_fragments, snapshot.final_collected
        final_symbol = "\u2713" if f else "\u2717"  # ✓ / ✗
        self._text = f"Relics: {c}/{t} | Final: {final_symbol}"

    # Optional hook for Arcade-based on_draw():
    # def on_draw(self):
    #     arcade.draw_text(self._text, x, y, color, font_size)
