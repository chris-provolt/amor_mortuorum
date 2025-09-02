from __future__ import annotations

import logging
import os
from typing import Optional

from .engine.loop import GameEngine, GameConfig

logger = logging.getLogger(__name__)


def _arcade_available() -> bool:
    try:
        import arcade  # noqa: F401
        return True
    except Exception:
        return False


def run_gui(max_steps: Optional[int] = None, tick_rate: float = 60.0) -> int:
    """Run the MVP with an Arcade GUI if available, otherwise fallback to headless.

    Args:
        max_steps: Optional stop after N updates; None runs until window closed.
        tick_rate: Target updates per second for GUI mode.

    Returns:
        Process exit code (0 on success).
    """
    if not _arcade_available():
        logger.warning("Arcade not available; falling back to headless mode")
        return run_headless(max_steps=max_steps, tick_rate=tick_rate)

    import arcade

    class GameWindow(arcade.Window):
        def __init__(self) -> None:
            # Choose a modest default size; can be adapted later
            super().__init__(800, 600, title="Amor Mortuorum - MVP")
            arcade.set_background_color(arcade.color.BLACK)
            # For predictable timing in MVP, do not v-sync lock (Arcade 3 uses pyglet clock)
            self.engine = GameEngine(GameConfig(tick_rate=tick_rate, max_steps=max_steps))
            self.engine.start()
            # Draw state
            self._message = "Amor Mortuorum - MVP\nPress ESC to quit"

        def on_draw(self):
            self.clear()
            arcade.draw_text(
                self._message,
                start_x=40,
                start_y=self.height // 2,
                color=arcade.color.ASH_GREY,
                font_size=20,
                multiline=True,
                width=self.width - 80,
                align="left",
            )
            arcade.draw_text(
                f"Ticks: {self.engine.step}",
                start_x=40,
                start_y=40,
                color=arcade.color.DARK_SPRING_GREEN,
                font_size=16,
            )

        def on_update(self, delta_time: float):
            # Arcade drives timing; we pass along dt to the engine
            if self.engine.running:
                self.engine.update(delta_time)
            else:
                # Close when engine self-stops (e.g., max_steps reached)
                self.close()

        def on_key_press(self, symbol: int, modifiers: int):
            if symbol == arcade.key.ESCAPE:
                self.engine.stop()
                self.close()

    window = GameWindow()
    try:
        logger.info("Launching Arcade window")
        arcade.run()
        logger.info("Arcade loop finished")
        return 0
    except Exception:
        logger.exception("Unhandled exception in GUI loop; exiting with code 1")
        return 1
    finally:
        try:
            window.close()
        except Exception:
            pass


def run_headless(max_steps: Optional[int] = 60, tick_rate: float = 30.0) -> int:
    """Run the MVP in a headless console loop.

    Args:
        max_steps: Stop after N updates; defaults to 60.
        tick_rate: Target updates per second for headless mode.
    """
    if max_steps is None:
        # Safety in CI/headless: always bound the loop
        max_steps = 60

    print("Amor Mortuorum - MVP (headless)")
    print("Press Ctrl+C to exit. Running...\n")

    engine = GameEngine(GameConfig(tick_rate=tick_rate, max_steps=max_steps))
    try:
        engine.run()
        print(f"Loop complete (steps={engine.step})")
        return 0
    except KeyboardInterrupt:
        engine.stop()
        print("Interrupted by user")
        return 130
    except Exception:
        logger.exception("Unhandled exception in headless loop")
        return 1


def run_auto(max_steps: Optional[int] = None, tick_rate: float = 60.0) -> int:
    """Run GUI if available and not explicitly overridden, else headless.

    Honors environment overrides:
      - AMOR_HEADLESS=1 forces headless.
      - AMOR_GUI=1 forces GUI (if arcade importable).
    """
    headless_env = os.getenv("AMOR_HEADLESS")
    gui_env = os.getenv("AMOR_GUI")

    if headless_env == "1":
        return run_headless(max_steps=max_steps, tick_rate=tick_rate)

    if gui_env == "1":
        return run_gui(max_steps=max_steps, tick_rate=tick_rate)

    # Default preference: GUI if available
    return run_gui(max_steps=max_steps, tick_rate=tick_rate)
