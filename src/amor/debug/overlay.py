from __future__ import annotations

import platform
import sys
import tracemalloc
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..config import AppConfig
from ..core.seed import SeedManager, monotonic_time
from ..telemetry.logger import TelemetryClient


@dataclass
class OverlayProviders:
    fps: Optional[Callable[[], Optional[float]]] = None
    frame_time_ms: Optional[Callable[[], Optional[float]]] = None


class DebugOverlay:
    """
    Headless-friendly Debug Overlay.

    Produces lines of diagnostic text; can optionally render via Arcade if available.
    Integrates with SeedManager and TelemetryClient, and surfaces memory usage via tracemalloc.
    """

    def __init__(
        self,
        config: AppConfig,
        seed_manager: Optional[SeedManager] = None,
        telemetry: Optional[TelemetryClient] = None,
        providers: Optional[OverlayProviders] = None,
    ) -> None:
        self.config = config
        self.seed_manager = seed_manager or SeedManager()
        self.telemetry = telemetry
        self.providers = providers or OverlayProviders()
        self.visible = bool(config.debug_overlay or config.debug_enabled)
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self._start_time = monotonic_time()

    def toggle(self) -> None:
        self.visible = not self.visible

    def uptime_seconds(self) -> float:
        return max(0.0, monotonic_time() - self._start_time)

    def _mem_info(self) -> str:
        curr, peak = tracemalloc.get_traced_memory()
        return f"{curr/1024:.1f} KB (peak {peak/1024:.1f} KB)"

    def lines(self) -> List[str]:
        lines: List[str] = []
        lines.append(f"{self.config.app_name} [DEBUG]")
        lines.append(f"Build: {self.config.build_version}")
        lines.append(f"Python: {platform.python_version()} ({sys.platform})")
        lines.append(f"Uptime: {self.uptime_seconds():.2f}s")
        # RNG / Seed
        seed_str = str(self.seed_manager.seed) if self.seed_manager.seed is not None else "(unset)"
        lines.append(f"Seed: {seed_str}")
        # Perf providers
        if self.providers.fps:
            fps = self.providers.fps()  # type: ignore
            if fps is not None:
                lines.append(f"FPS: {fps:.1f}")
        if self.providers.frame_time_ms:
            ft = self.providers.frame_time_ms()  # type: ignore
            if ft is not None:
                lines.append(f"Frame: {ft:.2f} ms")
        lines.append(f"Memory: {self._mem_info()}")
        # Telemetry
        if self.telemetry and self.telemetry.enabled:
            lines.append(f"Telemetry: ON → {self.telemetry.output_file}")
        else:
            lines.append("Telemetry: OFF")
        return lines

    def to_text(self) -> str:
        return "\n".join(self.lines())

    def draw(self, x: int = 10, y: int = 10) -> None:
        """
        Attempt to render overlay using Arcade if installed.
        Safe no-op in headless/test environments.
        """
        if not self.visible:
            return
        try:
            import arcade  # type: ignore
        except Exception:
            # Fallback: print to stdout once per call; consumers can redirect as needed
            print(self.to_text())
            return
        # Render a semi-transparent background and text lines
        padding = 8
        line_height = 16
        lines = self.lines()
        width = max(len(l) for l in lines) * 7 + padding * 2
        height = len(lines) * line_height + padding * 2
        # Background rectangle
        arcade.draw_lrtb_rectangle_filled(x, x + width, y + height, y, (0, 0, 0, 160))
        # Text
        ty = y + height - padding - line_height
        for l in lines:
            arcade.draw_text(l, x + padding, ty, (255, 255, 255, 255), 12)
            ty -= line_height
