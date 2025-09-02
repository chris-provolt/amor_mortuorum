from __future__ import annotations

from typing import Dict, Callable

from .base import BaseBoss


class BossRegistry:
    def __init__(self) -> None:
        self._factories: Dict[str, Callable[..., BaseBoss]] = {}

    def register(self, boss_id: str, factory: Callable[..., BaseBoss]) -> None:
        self._factories[boss_id] = factory

    def create(self, boss_id: str, *args, **kwargs) -> BaseBoss:
        if boss_id not in self._factories:
            raise KeyError(f"Unknown boss id: {boss_id}")
        return self._factories[boss_id](*args, **kwargs)


registry = BossRegistry()
