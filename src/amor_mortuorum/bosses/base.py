from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..core.events import EventBus
from ..core.save import SaveService
from ..combat.actors import Party


@dataclass
class PhaseDefinition:
    id: str
    threshold_pct: float  # 0..1 inclusive. Phase becomes active at or below this boss HP fraction
    music_track: str
    enter_sfx: str


class BossPhase:
    """
    Encapsulates per-phase AI hooks and audiovisual cues.
    """

    def __init__(
        self,
        definition: PhaseDefinition,
        on_choose_action: Callable[["BaseBoss", Party], "Action"],
        on_enter: Optional[Callable[["BaseBoss"], None]] = None,
    ) -> None:
        self.definition = definition
        self.on_choose_action = on_choose_action
        self.on_enter = on_enter


class BaseBoss:
    """Base boss entity with phases, AI and lifecycle hooks."""

    def __init__(
        self,
        name: str,
        max_hp: int,
        bus: EventBus,
        save: SaveService,
        phases: List[BossPhase],
        death_sfx: str = "sfx.boss.death",
        relic_id: Optional[str] = None,
        clear_flag: Optional[str] = None,
    ) -> None:
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self._bus = bus
        self._save = save
        self._phases = phases
        self._current_phase_index = 0
        self._turn = 0
        self._death_sfx = death_sfx
        self._relic_id = relic_id
        self._clear_flag = clear_flag
        # Cooldowns accessible to AI hooks
        self.cooldowns: Dict[str, int] = {}
        # Status flags like 'enraged'
        self.status: Dict[str, bool] = {}

    @property
    def phase(self) -> BossPhase:
        return self._phases[self._current_phase_index]

    def start_battle(self) -> None:
        # Enter initial phase audiovisuals
        self._enter_phase(0)

    def _enter_phase(self, idx: int) -> None:
        self._current_phase_index = idx
        pdef = self._phases[idx].definition
        # Broadcast music and SFX
        self._bus.publish("music.change", {"track": pdef.music_track, "boss": self.name, "phase": pdef.id})
        self._bus.publish("sfx.play", {"key": pdef.enter_sfx, "boss": self.name, "phase": pdef.id})
        # Call custom on_enter if any
        if self._phases[idx].on_enter:
            self._phases[idx].on_enter(self)

    def update_phase_if_needed(self) -> None:
        hp_frac = self.hp / max(1, self.max_hp)
        target_index = self._current_phase_index
        for i, p in enumerate(self._phases):
            if hp_frac <= p.definition.threshold_pct:
                target_index = max(target_index, i)
        if target_index != self._current_phase_index:
            self._enter_phase(target_index)

    def choose_action(self, party: Party) -> "Action":
        return self.phase.on_choose_action(self, party)

    def take_turn(self, party: Party) -> Dict:
        self.update_phase_if_needed()
        # Tick down cooldowns at start of boss turn
        for k in list(self.cooldowns.keys()):
            if self.cooldowns[k] > 0:
                self.cooldowns[k] -= 1
        act = self.choose_action(party)
        self._turn += 1
        return act.execute(self, party)

    def receive_damage(self, amount: int) -> int:
        before = self.hp
        self.hp = max(0, self.hp - max(0, amount))
        if self.hp == 0:
            self.on_defeat()
        else:
            self.update_phase_if_needed()
        return before - self.hp

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, amount))
        return self.hp - before

    def on_defeat(self) -> None:
        # Play death SFX
        self._bus.publish("sfx.play", {"key": self._death_sfx, "boss": self.name})
        # Clear music
        self._bus.publish("music.stop", {"boss": self.name})
        # Record clear condition
        if self._clear_flag:
            self._save.set_flag(self._clear_flag, True)
        if self._relic_id and not self._save.has_relic(self._relic_id):
            self._save.award_relic(self._relic_id)


# Late import to avoid circulars for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # pragma: no cover
    from ..combat.actions import Action
