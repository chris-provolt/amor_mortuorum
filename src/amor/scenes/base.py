from __future__ import annotations

from typing import Optional


class Scene:
    """Base Scene interface."""

    name: str = "scene"

    def on_enter(self, previous: Optional["Scene"]) -> None:
        """Called when the scene becomes active."""
        # Default: no-op
        return

    def on_exit(self, next_scene: Optional["Scene"]) -> None:
        """Called when the scene is about to be replaced."""
        # Default: no-op
        return
