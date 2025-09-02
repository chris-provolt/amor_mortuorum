from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from amor_mortuorum.core.audio import AudioManager, NullAudioManager
from amor_mortuorum.core.party import Party

logger = logging.getLogger(__name__)

# Name of the sound cue to play when resting at the Mausoleum
REST_SOUND_CUE = "mausoleum_rest"


@dataclass(frozen=True)
class RestResult:
    """Result of a Mausoleum rest action."""

    message: str
    healed_members: int
    revived_members: int
    sound_played: bool


CONFIRMATION_TEXT = (
    "The Mausoleum's embrace restores your party to full strength."
)


def rest_at_mausoleum(
    party: Party,
    audio: Optional[AudioManager] = None,
    revive_downed: bool = True,
) -> RestResult:
    """Fully restore party HP/MP and optionally play a sound cue.

    Args:
        party: The player's party to restore.
        audio: An AudioManager. If provided and the cue is available, a sound
            cue will be played. If None, a NullAudioManager is used.
        revive_downed: If True, downed members (0 HP) will be revived and fully
            restored.

    Returns:
        RestResult containing a confirmation message and details of the action.
    """
    if party is None:
        raise ValueError("party must not be None")

    logger.debug("Rest at Mausoleum initiated (revive_downed=%s)", revive_downed)
    healed, revived = party.restore_all(revive_downed=revive_downed)

    # Handle audio cue if available
    audio_mgr = audio or NullAudioManager()
    sound_played = False
    try:
        if audio_mgr.has_cue(REST_SOUND_CUE):
            audio_mgr.play(REST_SOUND_CUE)
            sound_played = True
            logger.info("Played rest sound cue: %s", REST_SOUND_CUE)
        else:
            logger.debug("Rest sound cue '%s' not available; skipping.", REST_SOUND_CUE)
    except Exception as exc:  # Be resilient; don't fail rest due to audio errors
        logger.warning("Error while attempting to play rest sound cue: %s", exc)

    result = RestResult(
        message=CONFIRMATION_TEXT,
        healed_members=healed,
        revived_members=revived,
        sound_played=sound_played,
    )
    logger.debug(
        "Mausoleum rest completed: healed=%d revived=%d sound_played=%s",
        healed,
        revived,
        sound_played,
    )
    return result
