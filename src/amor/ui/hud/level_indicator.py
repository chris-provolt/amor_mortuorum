from __future__ import annotations

from typing import Callable, Optional


class LevelIndicator:
    """Small HUD helper that formats the player's level for display.

    Integrates with Arcade by calling draw() in your UI layer, but can be
    used without Arcade for testability (get_label()).
    """

    def __init__(self, get_level: Callable[[], int], prefix: str = "Lv.", color: Optional[tuple] = None) -> None:
        self._get_level = get_level
        self.prefix = prefix
        self.color = color or (255, 255, 255)

    def get_label(self) -> str:
        return f"{self.prefix} {int(self._get_level())}"

    def draw(self, x: float, y: float, font_size: int = 16) -> None:
        """Draw the label via Arcade if available. No-op if Arcade is missing.
        This indirection prevents hard dependency in non-graphical test runs.
        """
        try:
            import arcade  # type: ignore
        except Exception:
            return
        arcade.draw_text(self.get_label(), x, y, self.color, font_size)
