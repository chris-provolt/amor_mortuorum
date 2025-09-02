from __future__ import annotations
import logging
from typing import Optional

from ..config import GenerationSettings
from .generator import CellularGenerator, DungeonGenerator, RoomsGenerator
from .tiles import MapGrid

logger = logging.getLogger(__name__)


class DungeonFactory:
    """Factory to produce dungeons using the selected algorithm.

    Usage:
      settings = GenerationSettings.from_env()
      dungeon = DungeonFactory.generate(settings)
    """

    @staticmethod
    def build_generator(settings: GenerationSettings) -> DungeonGenerator:
        algo = (settings.algorithm or "bsp").lower()
        if algo in ("bsp", "rooms", "bsp_rooms"):
            logger.info("DungeonFactory: using RoomsGenerator (algorithm=%s)", algo)
            return RoomsGenerator(
                max_rooms=settings.max_rooms,
                room_min_size=settings.room_min_size,
                room_max_size=settings.room_max_size,
            )
        elif algo in ("cellular", "cave", "cavern"):
            logger.info("DungeonFactory: using CellularGenerator (algorithm=%s)", algo)
            return CellularGenerator(
                initial_wall_prob=settings.cell_initial_wall_prob,
                smooth_steps=settings.cell_smooth_steps,
                wall_threshold=settings.cell_wall_threshold,
                min_floor_fraction=settings.cell_min_floor_fraction,
            )
        else:
            logger.warning(
                "Unknown algorithm '%s', falling back to RoomsGenerator", algo
            )
            return RoomsGenerator(
                max_rooms=settings.max_rooms,
                room_min_size=settings.room_min_size,
                room_max_size=settings.room_max_size,
            )

    @staticmethod
    def generate(settings: GenerationSettings, seed: Optional[int] = None) -> MapGrid:
        gen = DungeonFactory.build_generator(settings)
        return gen.generate(settings.width, settings.height, seed if seed is not None else settings.seed)
