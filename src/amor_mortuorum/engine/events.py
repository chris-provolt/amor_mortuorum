from enum import Enum, auto


class GameEvent(Enum):
    """Events emitted by GameState to notify UI or systems."""

    PLAYER_MOVED = auto()
    FLOOR_CHANGED = auto()
