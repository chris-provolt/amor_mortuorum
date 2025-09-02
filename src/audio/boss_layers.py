from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from .engine import TrackPlayer
from .mixer import AudioMixer

logger = logging.getLogger(__name__)


@dataclass
class BossLayerConfig:
    """Configuration for dynamic boss overlay layers."""

    miniboss_volume: float = 0.85
    final_boss_volume: float = 0.95
    fade_in_seconds: float = 1.5
    fade_out_seconds: float = 1.5


class BossLayerController:
    """Controls additional music layers that fade in/out during boss fights.

    Usage:
    - Register layer tracks via mixer.register_track("miniboss_overlay", player)
      and mixer.register_track("final_boss_overlay", player)
    - Call enter_miniboss() when a miniboss fight starts
    - Call exit_miniboss() when it ends
    - Call enter_final_boss() for the final boss; if already in a miniboss,
      call escalate_to_final() to crossfade overlays
    - Ensure mixer.tick(dt) is called once per frame

    The controller ensures:
    - Smooth fades (no clicks/pops) via linear ramps
    - Idempotent operations (re-enter calls won't stack)
    - Tracks stop at zero volume after fade-out to free resources
    """

    def __init__(
        self,
        mixer: AudioMixer,
        *,
        miniboss_track_name: str = "miniboss_overlay",
        final_boss_track_name: str = "final_boss_overlay",
        config: Optional[BossLayerConfig] = None,
    ) -> None:
        self.mixer = mixer
        self.miniboss_track_name = miniboss_track_name
        self.final_boss_track_name = final_boss_track_name
        self.config = config or BossLayerConfig()

        self._state: str = "idle"  # idle|miniboss|final

    # -----------------
    # Public API
    # -----------------

    def attach_tracks(self, tracks: Dict[str, TrackPlayer]) -> None:
        """Convenience: register track players to the mixer by name."""
        for name, player in tracks.items():
            self.mixer.register_track(name, player)

    def enter_miniboss(self) -> None:
        if self._state == "final":
            logger.debug("Already in final boss state; ignoring enter_miniboss")
            return
        logger.info("Entering miniboss: fading in layer")
        self._state = "miniboss"
        self._fade_in(self.miniboss_track_name, self.config.miniboss_volume)
        # Ensure final layer is not audible
        self._fade_out(self.final_boss_track_name)

    def exit_miniboss(self) -> None:
        if self._state != "miniboss":
            logger.debug("exit_miniboss called, but state is %s", self._state)
            # Still ensure overlays are off
            self._fade_out(self.miniboss_track_name)
            self._fade_out(self.final_boss_track_name)
            return
        logger.info("Exiting miniboss: fading out layer")
        self._state = "idle"
        self._fade_out(self.miniboss_track_name)

    def enter_final_boss(self) -> None:
        logger.info("Entering final boss: fading in final layer")
        self._state = "final"
        # Crossfade from miniboss layer (if any) to final layer
        self._fade_out(self.miniboss_track_name)
        self._fade_in(self.final_boss_track_name, self.config.final_boss_volume)

    def exit_final_boss(self) -> None:
        if self._state != "final":
            logger.debug("exit_final_boss called, but state is %s", self._state)
        logger.info("Exiting final boss: fading out final layer")
        self._state = "idle"
        self._fade_out(self.final_boss_track_name)

    def escalate_miniboss_to_final(self) -> None:
        """If already in a miniboss, escalate to final with a crossfade."""
        if self._state != "miniboss":
            # If not in miniboss, treat as entering final boss fresh.
            self.enter_final_boss()
            return
        logger.info("Escalating miniboss -> final: crossfading overlays")
        self._state = "final"
        self._fade_out(self.miniboss_track_name)
        self._fade_in(self.final_boss_track_name, self.config.final_boss_volume)

    # -----------------
    # Internal helpers
    # -----------------

    def _fade_in(self, track_name: str, target_volume: float) -> None:
        try:
            # Start from current volume; mixer will start playback if stopped
            self.mixer.fade_to(
                track_name,
                target_volume,
                self.config.fade_in_seconds,
            )
        except KeyError:
            logger.warning("Fade-in called for unregistered track: %s", track_name)

    def _fade_out(self, track_name: str) -> None:
        try:
            self.mixer.fade_to(
                track_name,
                0.0,
                self.config.fade_out_seconds,
                stop_at_zero=True,
            )
        except KeyError:
            logger.debug("Fade-out called for unregistered track: %s", track_name)
