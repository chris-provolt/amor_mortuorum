from __future__ import annotations

from dataclasses import dataclass

from ..combat.core import Controller, Entity, ShieldStatus, Stats


@dataclass
class Telegraph:
    message: str


class BaseMiniboss(Controller):
    """Base controller for minibosses with helper utilities.

    Each miniboss must:
    - implement a single distinct mechanic
    - emit a unique telegraph that communicates the mechanic
    """

    name: str = "Miniboss"

    def telegraph(self, entity: Entity, msg: str, ctx) -> None:
        ctx.log.telegraph(entity.name, msg)

    def give_opening_shield(self, entity: Entity, ctx, amount: int, message: str) -> None:
        entity.add_status(ShieldStatus(points=amount), ctx)
        self.telegraph(entity, message, ctx)

    @staticmethod
    def build(stats: Stats, name: str, team: str = "enemies") -> Entity:
        return Entity(name=name, team=team, stats=stats)

