from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

from ...core.party import Party, PartySlotView

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlotViewModel:
    """View model for a single party slot in the HUD."""

    index: int
    is_empty: bool
    name: str
    hp_text: str
    mp_text: str
    is_dead: bool


class PartyHUDModelBuilder:
    """Builds view-models for rendering a 4-slot party HUD.

    This builder is renderer-agnostic. It's intended for both runtime use and
    unit testing, ensuring empty slots are represented explicitly.
    """

    empty_placeholder: str = "—"

    def build(self, party: Party) -> List[SlotViewModel]:
        views: List[SlotViewModel] = []
        for sv in party.as_slot_views():
            views.append(self._build_slot_vm(sv))
        return views

    def _build_slot_vm(self, slot_view: PartySlotView) -> SlotViewModel:
        if slot_view.is_empty:
            return SlotViewModel(
                index=slot_view.index,
                is_empty=True,
                name=self.empty_placeholder,
                hp_text=f"{self.empty_placeholder}/{self.empty_placeholder}",
                mp_text=f"{self.empty_placeholder}/{self.empty_placeholder}",
                is_dead=False,
            )
        name = slot_view.name
        hp_text = f"{slot_view.hp}/{slot_view.max_hp}"
        mp_text = f"{slot_view.mp}/{slot_view.max_mp}"
        return SlotViewModel(
            index=slot_view.index,
            is_empty=False,
            name=name,
            hp_text=hp_text,
            mp_text=mp_text,
            is_dead=slot_view.is_dead,
        )


def try_render_arcade_party_hud(
    party: Party,
    origin: Tuple[float, float] = (16, 16),
    slot_size: Tuple[float, float] = (180, 56),
    slot_gap: float = 8.0,
    font_size: int = 12,
    dead_tint: Tuple[int, int, int] = (180, 60, 60),
) -> Optional[List[object]]:
    """Render the party HUD via Arcade if available.

    Returns a list of created Arcade drawables (for advanced usage) or None if
    Arcade is not installed. Rendering is side-effectful; tests should validate
    the model builder instead of this function.
    """
    try:
        import arcade  # type: ignore
    except Exception as e:  # pragma: no cover - optional dependency not required for tests
        logger.warning("Arcade not available; skipping HUD render: %s", e)
        return None

    builder = PartyHUDModelBuilder()
    model = builder.build(party)

    x0, y0 = origin
    width, height = slot_size
    drawables: List[object] = []

    for i, slot in enumerate(model):
        x = x0
        y = y0 + i * (height + slot_gap)
        color = arcade.color.DARK_SLATE_GRAY if slot.is_empty else arcade.color.DARK_BLUE_GRAY
        if slot.is_dead and not slot.is_empty:
            color = dead_tint

        # Background rectangle
        rect = arcade.create_rectangle_filled(x + width / 2, y + height / 2, width, height, color)
        rect.draw()
        drawables.append(rect)

        # Text
        text_color = arcade.color.LIGHT_GRAY if slot.is_empty else arcade.color.WHITE
        t1 = arcade.draw_text(slot.name, x + 8, y + height - 20, text_color, font_size)
        t2 = arcade.draw_text(f"HP: {slot.hp_text}", x + 8, y + height - 36, text_color, font_size)
        t3 = arcade.draw_text(f"MP: {slot.mp_text}", x + 8, y + height - 52, text_color, font_size)
        drawables.extend([t1, t2, t3])

    return drawables
