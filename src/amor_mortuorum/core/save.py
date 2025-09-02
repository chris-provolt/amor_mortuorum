from __future__ import annotations

from typing import Any, Dict


class SaveService:
    """Interface for save persistence."""

    def set_flag(self, key: str, value: bool) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def get_flag(self, key: str, default: bool = False) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def award_relic(self, relic_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def has_relic(self, relic_id: str) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class InMemorySaveService(SaveService):
    """
    Test/deterministic in-memory save implementation.
    Stores flags and awarded relics in dictionaries.
    """

    def __init__(self) -> None:
        self._flags: Dict[str, bool] = {}
        self._relics: Dict[str, bool] = {}

    def set_flag(self, key: str, value: bool) -> None:
        self._flags[key] = value

    def get_flag(self, key: str, default: bool = False) -> bool:
        return self._flags.get(key, default)

    def award_relic(self, relic_id: str) -> None:
        self._relics[relic_id] = True

    def has_relic(self, relic_id: str) -> bool:
        return self._relics.get(relic_id, False)
