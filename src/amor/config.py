from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Global game settings relevant to determinism and generation.

    Attributes:
        seed: Master seed controlling deterministic generation. If None, a random seed
              will be created at runtime. Can be set via CLI or env var AMOR_SEED.
        width: Dungeon width (tiles).
        height: Dungeon height (tiles).
    """

    seed: Optional[Union[int, str]] = None
    width: int = 64
    height: int = 64


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="amor",
        description=(
            "Amor Mortuorum - seed controls for deterministic dungeon and chest generation"
        ),
    )
    parser.add_argument(
        "--seed",
        type=str,
        default=None,
        help=(
            "Master seed for deterministic generation (int or string). "
            "If omitted, uses env AMOR_SEED or generates a random seed."
        ),
    )
    parser.add_argument(
        "--floor",
        type=int,
        default=1,
        help="Dungeon floor index (1-99)."
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Override dungeon width (tiles)."
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Override dungeon height (tiles)."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging."
    )
    return parser.parse_args(argv)


def load_settings_from_env() -> dict:
    env_seed = os.getenv("AMOR_SEED")
    cfg: dict = {}
    if env_seed is not None:
        cfg["seed"] = env_seed
    env_width = os.getenv("AMOR_WIDTH")
    env_height = os.getenv("AMOR_HEIGHT")
    if env_width:
        try:
            cfg["width"] = int(env_width)
        except ValueError:
            logger.warning("Invalid AMOR_WIDTH value: %s", env_width)
    if env_height:
        try:
            cfg["height"] = int(env_height)
        except ValueError:
            logger.warning("Invalid AMOR_HEIGHT value: %s", env_height)
    return cfg


def build_settings(args: argparse.Namespace) -> Settings:
    env_cfg = load_settings_from_env()

    seed = args.seed if args.seed is not None else env_cfg.get("seed")
    width = args.width if args.width is not None else env_cfg.get("width", 64)
    height = args.height if args.height is not None else env_cfg.get("height", 64)

    return Settings(seed=seed, width=width, height=height)
