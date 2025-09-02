from dataclasses import dataclass
from typing import Optional, Tuple, List
from .entities import Actor
from .map import GridMap
from .damage import DamageService
from ..core.events import EventBus
from ..core.audio import AudioManager


@dataclass
class Trap:
    """Base trap class. Subclasses implement on_enter and update behaviors."""
    tid: str
    x: int
    y: int
    enabled: bool = True

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def on_enter(self, game: "GameState", actor: Actor) -> None:  # type: ignore[name-defined]
        pass

    def update(self, game: "GameState") -> None:  # type: ignore[name-defined]
        pass


@dataclass
class SpikeTrap(Trap):
    """Spikes deal step damage when an actor enters the tile.

    Simple instantaneous effect; relies on GameState.move_entity to call on_enter.
    """
    damage: int = 3

    def on_enter(self, game: "GameState", actor: Actor) -> None:  # type: ignore[name-defined]
        if not self.enabled:
            return
        source = "Spikes"
        game.bus.publish("trap_triggered", {"trap_id": self.tid, "trap_type": "spike", "x": self.x, "y": self.y, "target_id": actor.eid})
        game.damage.apply_damage(actor, self.damage, source, sfx_key="trap_spike")


@dataclass
class DartTrap(Trap):
    """Dart trap fires a projectile along a cardinal direction.

    - Fires if an actor is in LOS during update.
    - Otherwise fires on a periodic timer regardless of LOS.
    - Damage applies to the first entity encountered on the ray.
    - LOS is blocked by walls; range-limited.
    """
    direction: Tuple[int, int] = (1, 0)
    period_ticks: int = 5
    dart_damage: int = 2
    max_range: int = 8
    _cooldown: int = 0

    def __post_init__(self) -> None:
        # Initialize cooldown to period so it doesn't fire immediately unless LOS
        self._cooldown = self.period_ticks

    def update(self, game: "GameState") -> None:  # type: ignore[name-defined]
        if not self.enabled:
            return
        # If any actor in immediate LOS, fire now
        target = self._find_los_target(game.map)
        if target is not None:
            self._fire(game, target)
            self._cooldown = self.period_ticks
            return
        # Otherwise count down and fire when timer elapses
        self._cooldown -= 1
        if self._cooldown <= 0:
            # Fire even if no target in LOS; we still raycast and may hit something
            target2 = game.map.find_first_entity_in_line(self.pos, self.direction, self.max_range)
            if target2 is not None:
                self._fire(game, target2)
            else:
                # Emit generic fired event for UI/SFX
                game.bus.publish("trap_fired", {"trap_id": self.tid, "trap_type": "dart", "x": self.x, "y": self.y, "hit": False})
                game.audio.play_sfx("trap_dart")
            self._cooldown = self.period_ticks

    def _find_los_target(self, grid: GridMap) -> Optional[Actor]:
        # Return first entity in line if present
        return grid.find_first_entity_in_line(self.pos, self.direction, self.max_range)

    def _fire(self, game: "GameState", target: Actor) -> None:
        game.bus.publish("trap_fired", {"trap_id": self.tid, "trap_type": "dart", "x": self.x, "y": self.y, "hit": True, "target_id": target.eid})
        game.damage.apply_damage(target, self.dart_damage, "Dart Trap", sfx_key="trap_dart")


# Type hints require forward declaration for GameState; provided here for static tools only
class GameState:  # pragma: no cover - only for typing reference
    map: GridMap
    bus: EventBus
    audio: AudioManager
    damage: DamageService
