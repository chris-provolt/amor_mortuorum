"""Graveyard hub service: rest, shop, crypt, and the only place a full save happens."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..data import GameData
from ..persistence import MetaState, RunState, SaveError, SaveGame, SaveManager
from .crypt import CryptService
from .entities import Player
from .relics import apply_passives
from .run import Run
from .shop import Shop

logger = logging.getLogger(__name__)


@dataclass
class HubContext:
    meta: MetaState
    shop: Shop
    crypt: CryptService


class GraveyardHub:
    """Orchestrates a Graveyard visit.

    - ``enter()`` bumps ``meta.hub_cycle``, restocks the shop deterministically
      from ``(meta.meta_seed, meta.hub_cycle)``, and persists meta.
    - ``rest()`` fully heals a player.
    - ``crypt_deposit`` / ``crypt_withdraw`` persist the crypt after each change.
    - ``save_run()`` writes the full save (meta + run) while in the Graveyard.
    """

    def __init__(self, save_manager: SaveManager, data: GameData, meta: Optional[MetaState] = None):
        self.save_manager = save_manager
        self.data = data
        self._meta = meta
        self._ctx: Optional[HubContext] = None

    def _load_meta(self) -> MetaState:
        if self._meta is not None:
            return self._meta
        try:
            self._meta = self.save_manager.load_meta()
        except SaveError:
            self._meta = MetaState()
        return self._meta

    def enter(self) -> HubContext:
        meta = self._load_meta()
        meta.hub_cycle += 1
        shop = Shop(self.data)
        shop.restock(seed=meta.meta_seed, cycle=meta.hub_cycle)
        crypt = CryptService(meta.crypt, self.data)
        self._ctx = HubContext(meta=meta, shop=shop, crypt=crypt)
        self.save_manager.save_meta(meta)
        logger.info("Entered Graveyard hub: cycle=%s", meta.hub_cycle)
        return self._ctx

    @property
    def ctx(self) -> HubContext:
        if self._ctx is None:
            raise RuntimeError("Hub not entered. Call enter() first.")
        return self._ctx

    @property
    def meta(self) -> MetaState:
        return self._load_meta()

    def rest(self, player: Player) -> None:
        player.heal_full()
        logger.info("%s rested at the Graveyard and is fully healed.", player.name)

    def crypt_deposit(self, player: Player, item_id: str, quantity: int = 1) -> None:
        self.ctx.crypt.deposit(player, item_id, quantity)
        self.save_manager.save_meta(self.ctx.meta)

    def crypt_withdraw(
        self, player: Player, slot_index: int, quantity: Optional[int] = None
    ) -> None:
        self.ctx.crypt.withdraw(player, slot_index, quantity)
        self.save_manager.save_meta(self.ctx.meta)

    def save_run(self, run: Run) -> SaveGame:
        """Full save of meta + run; only legal while the run is in the Graveyard."""
        run.in_graveyard = True
        save = SaveGame(
            meta=self.meta, run=run.to_run_state(), profile_id=self.save_manager.profile_id
        )
        self.save_manager.save_full(save)
        logger.info("Run saved at the Graveyard (floor %d)", run.floor)
        return save

    def load_run(self) -> Optional[Run]:
        """Return the saved run if one exists and was saved in the Graveyard."""
        try:
            save = self.save_manager.load_full()
        except SaveError:
            return None
        state: Optional[RunState] = save.run
        if state is None or not state.in_graveyard or not state.party:
            return None
        run = Run.from_run_state(state)
        apply_passives(run, self.meta, self.data)
        return run

    def end_run(self, run: Run) -> None:
        """Record a finished run in meta and clear the stored run state."""
        meta = self.meta
        meta.runs_completed += 1
        meta.deepest_floor = max(meta.deepest_floor, run.floor)
        self.save_manager.save_meta(meta)
        self.save_manager.clear_run()
