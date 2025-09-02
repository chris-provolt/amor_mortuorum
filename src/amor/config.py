import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GenerationSettings:
    """Configuration for dungeon generation.

    Selection is done primarily via environment variable AMOR_DUNGEON_ALGO.
    Supported values: "bsp" (rooms + corridors) and "cellular" (cellular automata caverns).

    The rest of parameters are algorithm-specific defaults that can be overridden
    programmatically or via environment variables.
    """

    # Algorithm selection: "bsp" or "cellular"
    algorithm: str = "bsp"

    # Global map dimensions
    width: int = 80
    height: int = 48

    # Random seed (optional); if None, random randomness is used
    seed: Optional[int] = None

    # Rooms algorithm (BSP/rooms) parameters
    max_rooms: int = 18
    room_min_size: int = 4
    room_max_size: int = 10

    # Cellular algorithm parameters
    cell_initial_wall_prob: float = 0.45
    cell_smooth_steps: int = 5
    cell_wall_threshold: int = 5
    cell_min_floor_fraction: float = 0.28

    @staticmethod
    def from_env() -> "GenerationSettings":
        """Build settings from environment variables, providing sensible defaults.

        Environment variables:
          - AMOR_DUNGEON_ALGO: one of {"bsp", "cellular"}
          - AMOR_WIDTH, AMOR_HEIGHT
          - AMOR_SEED
          - AMOR_MAX_ROOMS, AMOR_ROOM_MIN, AMOR_ROOM_MAX
          - AMOR_CELL_INIT_P, AMOR_CELL_STEPS, AMOR_CELL_T, AMOR_CELL_MIN_F
        """
        algo = os.getenv("AMOR_DUNGEON_ALGO", "bsp").strip().lower()
        width = int(os.getenv("AMOR_WIDTH", 80))
        height = int(os.getenv("AMOR_HEIGHT", 48))
        seed_env = os.getenv("AMOR_SEED")
        seed = int(seed_env) if seed_env not in (None, "", "none", "None") else None

        max_rooms = int(os.getenv("AMOR_MAX_ROOMS", 18))
        room_min = int(os.getenv("AMOR_ROOM_MIN", 4))
        room_max = int(os.getenv("AMOR_ROOM_MAX", 10))

        cell_init_p = float(os.getenv("AMOR_CELL_INIT_P", 0.45))
        cell_steps = int(os.getenv("AMOR_CELL_STEPS", 5))
        cell_t = int(os.getenv("AMOR_CELL_T", 5))
        cell_min_f = float(os.getenv("AMOR_CELL_MIN_F", 0.28))

        return GenerationSettings(
            algorithm=algo,
            width=width,
            height=height,
            seed=seed,
            max_rooms=max_rooms,
            room_min_size=room_min,
            room_max_size=room_max,
            cell_initial_wall_prob=cell_init_p,
            cell_smooth_steps=cell_steps,
            cell_wall_threshold=cell_t,
            cell_min_floor_fraction=cell_min_f,
        )
