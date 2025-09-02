from typing import List, Tuple, Optional
from .map import GridMap
from .entities import Actor
from .traps import Trap, SpikeTrap, DartTrap
from .damage import DamageService
from ..core.events import EventBus
from ..core.audio import AudioManager


class GameState:
    """Orchestrates the map, entities, traps, and services.

    - Provides movement to trigger spike traps.
    - Ticks to update timed/LOS traps (dart traps).
    - Emits events and SFX via injected services.
    """

    def __init__(self, width: int, height: int) -> None:
        self.map = GridMap(width, height)
        self.entities: List[Actor] = []
        self.traps: List[Trap] = []
        self.bus = EventBus()
        self.audio = AudioManager()
        self.damage = DamageService(self.bus, self.audio)

    # Entity lifecycle
    def add_entity(self, actor: Actor) -> None:
        self.entities.append(actor)
        self.map.register_entity(actor)

    def remove_entity(self, actor: Actor) -> None:
        if actor in self.entities:
            self.entities.remove(actor)
        self.map.unregister_entity(actor)

    # Trap lifecycle
    def add_trap(self, trap: Trap) -> None:
        self.traps.append(trap)

    # Movement
    def move_entity(self, actor: Actor, dx: int, dy: int) -> bool:
        nx = actor.x + dx
        ny = actor.y + dy
        if self.map.is_blocking(nx, ny):
            return False
        actor.move_to(nx, ny)
        # Trigger on_enter traps located at new tile
        for trap in list(self.traps):
            if trap.enabled and trap.pos == (nx, ny):
                trap.on_enter(self, actor)
        return True

    # Tick update
    def tick(self) -> None:
        for trap in list(self.traps):
            trap.update(self)
