from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from ..events import get_event_bus
from ..events.types import EventType
from ..stats.modifiers import GlobalModifiers
from .relics import RELICS

logger = logging.getLogger(__name__)


@dataclass
class RelicToggleState:
    """Represents toggle state of a single relic."""

    owned: bool = False
    enabled: bool = False


class RelicPassiveManager:
    """Manages ownership and toggling of Relic passives and computes global effects.

    Core responsibilities:
      - Track which relics are owned and which are enabled.
      - Aggregate enabled relic effects into a single GlobalModifiers instance.
      - Publish events when toggle states change and when aggregate modifiers change.

    All changes publish EventType.RELIC_TOGGLE_CHANGED and EventType.RELIC_PASSIVES_CHANGED.
    """

    def __init__(self) -> None:
        self._state: Dict[str, RelicToggleState] = {
            relic_id: RelicToggleState(owned=False, enabled=False) for relic_id in RELICS.keys()
        }
        self._cached_mods: Optional[GlobalModifiers] = None
        self._bus = get_event_bus()

    # --- Ownership management ---
    def acquire_relic(self, relic_id: str) -> None:
        if relic_id not in RELICS:
            raise KeyError(f"Unknown relic '{relic_id}'")
        st = self._state[relic_id]
        if not st.owned:
            st.owned = True
            logger.info("Relic acquired: %s", relic_id)
            # Default: newly acquired relics start disabled; user must opt-in
            self._emit_toggle_changed(relic_id)

    def set_owned(self, relic_id: str, owned: bool) -> None:
        if relic_id not in RELICS:
            raise KeyError(f"Unknown relic '{relic_id}'")
        st = self._state[relic_id]
        if st.owned != owned:
            st.owned = owned
            if not owned:
                st.enabled = False
            self._emit_toggle_changed(relic_id)
            self._recalc_and_emit()

    def set_owned_many(self, relic_ids: Iterable[str]) -> None:
        ids = set(relic_ids)
        for rid in RELICS.keys():
            self.set_owned(rid, rid in ids)

    # --- Toggle management ---
    def enable(self, relic_id: str) -> None:
        self._set_enabled(relic_id, True)

    def disable(self, relic_id: str) -> None:
        self._set_enabled(relic_id, False)

    def toggle(self, relic_id: str) -> None:
        if relic_id not in RELICS:
            raise KeyError(f"Unknown relic '{relic_id}'")
        st = self._state[relic_id]
        self._set_enabled(relic_id, not st.enabled)

    def _set_enabled(self, relic_id: str, enabled: bool) -> None:
        if relic_id not in RELICS:
            raise KeyError(f"Unknown relic '{relic_id}'")
        st = self._state[relic_id]
        if not st.owned and enabled:
            raise PermissionError(f"Cannot enable relic '{relic_id}' that is not owned")
        if st.enabled != enabled:
            st.enabled = enabled if st.owned else False
            logger.info("Relic %s => %s", relic_id, "ENABLED" if st.enabled else "DISABLED")
            self._emit_toggle_changed(relic_id)
            self._recalc_and_emit()

    # --- Accessors ---
    def is_owned(self, relic_id: str) -> bool:
        return self._state[relic_id].owned

    def is_enabled(self, relic_id: str) -> bool:
        return self._state[relic_id].enabled

    def owned_relics(self) -> Set[str]:
        return {rid for rid, st in self._state.items() if st.owned}

    def enabled_relics(self) -> Set[str]:
        return {rid for rid, st in self._state.items() if st.enabled}

    def get_global_modifiers(self) -> GlobalModifiers:
        if self._cached_mods is None:
            self._cached_mods = self._compute_modifiers()
        return self._cached_mods

    # --- Persistence helpers ---
    def to_dict(self) -> Dict:
        return {
            "relics": {
                rid: {"owned": st.owned, "enabled": st.enabled} for rid, st in self._state.items()
            }
        }

    def load_dict(self, data: Dict) -> None:
        relics = data.get("relics", {}) if isinstance(data, dict) else {}
        changed_any = False
        for rid, st in self._state.items():
            entry = relics.get(rid, {})
            owned = bool(entry.get("owned", False))
            enabled = bool(entry.get("enabled", False))
            if st.owned != owned or st.enabled != (enabled if owned else False):
                st.owned = owned
                st.enabled = enabled if owned else False
                changed_any = True
                self._emit_toggle_changed(rid)
        if changed_any:
            self._recalc_and_emit()

    # --- Internal helpers ---
    def _compute_modifiers(self) -> GlobalModifiers:
        agg = GlobalModifiers()  # identity
        for rid, st in self._state.items():
            if not st.enabled:
                continue
            relic = RELICS[rid]
            agg = agg.combine(relic.effect)
        logger.debug("Computed aggregate modifiers: %s", agg)
        return agg

    def _emit_toggle_changed(self, relic_id: str) -> None:
        st = self._state[relic_id]
        self._bus.publish(
            EventType.RELIC_TOGGLE_CHANGED,
            {
                "relic_id": relic_id,
                "owned": st.owned,
                "enabled": st.enabled,
            },
        )

    def _recalc_and_emit(self) -> None:
        self._cached_mods = self._compute_modifiers()
        self._bus.publish(
            EventType.RELIC_PASSIVES_CHANGED,
            {"modifiers": self._cached_mods.to_dict()},
        )
