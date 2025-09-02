from typing import Set, List


class AudioManager:
    """Minimal SFX manager stub.

    - Allows registration of SFX keys that are considered 'available'.
    - play_sfx will no-op if the key is not registered ("if present").
    - Records played sfx keys for diagnostics/testing.
    """

    def __init__(self) -> None:
        self._available: Set[str] = set()
        self._played: List[str] = []

    def register_sfx(self, key: str) -> None:
        self._available.add(key)

    def play_sfx(self, key: str) -> None:
        if key in self._available:
            self._played.append(key)
        # else: "if present" semantics -> ignore silently

    @property
    def played(self) -> List[str]:
        return list(self._played)
