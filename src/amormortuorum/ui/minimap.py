from __future__ import annotations

from amormortuorum.state.session import GameSession


class Minimap:
    """
    Simple minimap controller that reflects/toggles visibility stored in GameSession.
    Rendering is handled elsewhere; this object represents the logic/state.
    """

    def __init__(self, session: GameSession):
        self._session = session

    @property
    def visible(self) -> bool:
        return self._session.minimap_visible

    def toggle(self) -> bool:
        return self._session.toggle_minimap()
