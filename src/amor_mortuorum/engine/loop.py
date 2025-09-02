from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Configuration for the MVP game loop.

    Attributes:
        tick_rate: Target updates per second for the loop. If 0 or None, updates as fast as possible.
        max_steps: If provided and > 0, the loop will automatically stop after this many updates.
    """

    tick_rate: float = 30.0
    max_steps: Optional[int] = None


class GameEngine:
    """A minimal, headless-friendly MVP game engine loop.

    This isolates the deterministic loop logic from any rendering backend so it can be tested
    and also driven by a GUI framework (e.g., Arcade) when available.
    """

    def __init__(self, config: Optional[GameConfig] = None) -> None:
        self.config = config or GameConfig()
        self._running: bool = False
        self._step: int = 0
        self._last_time: Optional[float] = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def step(self) -> int:
        return self._step

    def start(self) -> None:
        """Start the engine loop state.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self._running:
            logger.debug("GameEngine.start() called while already running")
            return
        self._running = True
        self._step = 0
        self._last_time = time.perf_counter()
        logger.info("GameEngine started (tick_rate=%s, max_steps=%s)", self.config.tick_rate, self.config.max_steps)

    def stop(self) -> None:
        """Stop the loop gracefully."""
        if not self._running:
            return
        self._running = False
        logger.info("GameEngine stopped at step=%s", self._step)

    def update(self, dt: float) -> None:
        """Perform a single update tick.

        Args:
            dt: Delta time in seconds since last update.
        """
        if not self._running:
            logger.debug("update() called while not running; ignored")
            return
        # MVP: do nothing but count steps; placeholder for future game state updates
        self._step += 1
        logger.debug("Tick #%d (dt=%.4f)", self._step, dt)

        # Auto stop if max_steps set
        if self.config.max_steps is not None and self._step >= self.config.max_steps:
            self.stop()

    def run(self) -> None:
        """Run a blocking loop until stopped or max_steps reached.

        This is a headless loop suitable for CLI mode. It throttles to tick_rate if configured.
        """
        self.start()
        target_dt = 0.0
        if self.config.tick_rate and self.config.tick_rate > 0:
            target_dt = 1.0 / float(self.config.tick_rate)

        while self._running:
            now = time.perf_counter()
            if self._last_time is None:
                dt = 0.0
            else:
                dt = now - self._last_time
            self._last_time = now

            self.update(dt)

            # Throttle to tick rate if configured
            if target_dt > 0:
                elapsed = time.perf_counter() - now
                remaining = target_dt - elapsed
                if remaining > 0:
                    time.sleep(remaining)

        logger.info("Loop complete (steps=%d)", self._step)
