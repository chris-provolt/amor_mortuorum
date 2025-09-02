from __future__ import annotations

import logging
from typing import Optional

from .base import Scene

logger = logging.getLogger(__name__)


class SceneManager:
    """Minimal scene manager to transition between scenes."""

    def __init__(self) -> None:
        self._active: Optional[Scene] = None

    @property
    def active_scene(self) -> Optional[Scene]:
        return self._active

    def transition_to(self, scene: Scene) -> None:
        prev = self._active
        if prev is not None:
            logger.debug("Exiting scene: %s", getattr(prev, "name", prev.__class__.__name__))
            prev.on_exit(scene)
        self._active = scene
        logger.debug("Entering scene: %s", getattr(scene, "name", scene.__class__.__name__))
        scene.on_enter(prev)
