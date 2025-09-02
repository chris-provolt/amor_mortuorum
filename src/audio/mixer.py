from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .engine import TrackPlayer

logger = logging.getLogger(__name__)


@dataclass
class FadeTask:
    """Represents a single linear fade for a track's volume.

    Attributes:
        track_name: Name of the track controlled by the mixer.
        start: Starting volume at t=0.
        target: Target volume at t=duration.
        duration: Total fade duration in seconds (> 0).
        elapsed: Time progressed so far in seconds.
        stop_at_zero: If True and target is 0, stop the track once fade completes.
        on_complete: Optional callback invoked when fade completes.
    """

    track_name: str
    start: float
    target: float
    duration: float
    elapsed: float = 0.0
    stop_at_zero: bool = False
    on_complete: Optional[Callable[[str], None]] = None

    def step(self, dt: float) -> float:
        """Advance the fade by dt seconds and return the new volume.

        Clamps to [0, 1] and ensures elapsed does not exceed duration.
        """
        if self.duration <= 0:
            self.elapsed = self.duration
            return self.target
        self.elapsed = min(self.elapsed + max(0.0, dt), self.duration)
        t = self.elapsed / self.duration
        # Linear interpolation
        vol = (1.0 - t) * self.start + t * self.target
        return max(0.0, min(1.0, vol))

    @property
    def done(self) -> bool:
        return self.elapsed >= self.duration


class AudioMixer:
    """Manages named audio tracks and smooth fades to avoid clicks/pops.

    - Register arbitrary TrackPlayer instances under readable names.
    - Drive fading by calling tick(delta_time) each frame.
    - Linear volume ramps avoid abrupt steps; callers can choose durations.
    - A single fade task per track; new fades replace old ones seamlessly by
      using the current volume as the new start to avoid jumps.
    """

    def __init__(self) -> None:
        self._tracks: Dict[str, TrackPlayer] = {}
        self._fades: Dict[str, FadeTask] = {}

    def register_track(self, name: str, player: TrackPlayer) -> None:
        if name in self._tracks:
            logger.debug("Replacing existing track registration: %s", name)
        self._tracks[name] = player

    def play(self, name: str, *, loop: bool = True, volume: float = 1.0) -> None:
        player = self._require(name)
        player.set_volume(max(0.0, min(1.0, volume)))
        player.play(loop=loop)

    def stop(self, name: str) -> None:
        player = self._require(name)
        player.stop()
        # Cancel any fade in progress for this track
        self._fades.pop(name, None)

    def set_volume(self, name: str, volume: float) -> None:
        player = self._require(name)
        player.set_volume(volume)

    def get_volume(self, name: str) -> float:
        return self._require(name).get_volume()

    def fade_to(
        self,
        name: str,
        target_volume: float,
        duration: float,
        *,
        stop_at_zero: bool = False,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Fade a track to the given volume over duration seconds.

        - If the track is not playing, it will be started with volume unchanged.
        - If another fade is in progress, it is replaced, using the current
          volume as the new start, thus avoiding clicks/pops.
        - If duration <= 0, the volume is set immediately and on_complete fires.
        """
        player = self._require(name)
        cur = player.get_volume()
        tgt = max(0.0, min(1.0, float(target_volume)))
        duration = float(max(0.0, duration))
        if not player.is_playing():
            # Start playing at current volume to avoid pops
            player.play(loop=True)
            player.set_volume(cur)
        if duration == 0.0:
            player.set_volume(tgt)
            self._fades.pop(name, None)
            if stop_at_zero and tgt <= 0.0:
                player.stop()
            if on_complete:
                try:
                    on_complete(name)
                except Exception:  # pragma: no cover - defensive log
                    logger.exception("fade_to on_complete error for %s", name)
            return
        task = FadeTask(
            track_name=name,
            start=cur,
            target=tgt,
            duration=duration,
            elapsed=0.0,
            stop_at_zero=stop_at_zero,
            on_complete=on_complete,
        )
        self._fades[name] = task

    def tick(self, dt: float) -> None:
        """Advance all fade tasks. Call once per frame from the main loop."""
        dt = float(max(0.0, dt))
        finished: list[str] = []
        for name, task in list(self._fades.items()):
            player = self._tracks.get(name)
            if not player:
                # Track was deregistered; drop the fade.
                finished.append(name)
                continue
            new_vol = task.step(dt)
            player.set_volume(new_vol)
            if task.done:
                finished.append(name)
                if task.stop_at_zero and task.target <= 0.0:
                    player.stop()
                if task.on_complete:
                    try:
                        task.on_complete(name)
                    except Exception:  # pragma: no cover
                        logger.exception("Fade on_complete callback failed for %s", name)
        # Cleanup finished fades
        for name in finished:
            self._fades.pop(name, None)

    def _require(self, name: str) -> TrackPlayer:
        if name not in self._tracks:
            raise KeyError(f"Track not registered: {name}")
        return self._tracks[name]

    def has_active_fade(self, name: str) -> bool:
        return name in self._fades
