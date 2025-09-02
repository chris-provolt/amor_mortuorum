from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from amormortuorum.core.scenes import Scene
from amormortuorum.ui.toast import ToastManager
from .model import SaveMeta
from .storage import SaveStorage

logger = logging.getLogger(__name__)


@dataclass
class SaveResult:
    success: bool
    message: str
    wrote_meta: bool
    code: str = "OK"  # OK | NOT_IN_GRAVEYARD | IO_ERROR | UNKNOWN


class SaveManager:
    """Coordinates save requests, enforcing Graveyard-only rule and feedback.

    The manager does not block the game loop. It returns a result and also
    posts a non-blocking toast message via ToastManager, satisfying the UX
    requirement for attempts outside the Graveyard.
    """

    NOTICE_NOT_IN_GRAVEYARD = "You can only save at the Graveyard."
    NOTICE_SAVE_SUCCESS = "Game saved."
    NOTICE_SAVE_ERROR = "Failed to save game."

    def __init__(self, storage: SaveStorage, ui_toasts: ToastManager) -> None:
        self._storage = storage
        self._toasts = ui_toasts
        self._allowed_scene = Scene.GRAVEYARD

    def can_save(self, scene: Scene) -> bool:
        return scene == self._allowed_scene

    def request_save(self, scene: Scene, meta: SaveMeta) -> SaveResult:
        """Attempt to save; only allowed in Graveyard.

        - If not in Graveyard: posts a warning toast and returns non-blocking result.
        - If in Graveyard: writes meta and posts a success or error toast.
        """
        if not self.can_save(scene):
            logger.info(
                "Save attempt blocked outside Graveyard (scene=%s)", scene.value
            )
            self._toasts.show(self.NOTICE_NOT_IN_GRAVEYARD, level="warning")
            return SaveResult(
                success=False,
                message=self.NOTICE_NOT_IN_GRAVEYARD,
                wrote_meta=False,
                code="NOT_IN_GRAVEYARD",
            )

        try:
            logger.debug("Saving meta in Graveyard: %s", meta)
            self._storage.write_meta(meta)
        except OSError as exc:
            logger.error("I/O error while writing meta: %s", exc)
            self._toasts.show(self.NOTICE_SAVE_ERROR, level="error")
            return SaveResult(
                success=False,
                message=self.NOTICE_SAVE_ERROR,
                wrote_meta=False,
                code="IO_ERROR",
            )
        except Exception as exc:  # pragma: no cover - unknown fatal issues
            logger.exception("Unexpected error during save: %s", exc)
            self._toasts.show(self.NOTICE_SAVE_ERROR, level="error")
            return SaveResult(
                success=False,
                message=self.NOTICE_SAVE_ERROR,
                wrote_meta=False,
                code="UNKNOWN",
            )

        self._toasts.show(self.NOTICE_SAVE_SUCCESS, level="success")
        return SaveResult(
            success=True,
            message=self.NOTICE_SAVE_SUCCESS,
            wrote_meta=True,
            code="OK",
        )
