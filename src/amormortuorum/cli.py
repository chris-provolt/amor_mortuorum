import argparse
import logging
import os
from pathlib import Path

from .core.settings import Settings
from .utils.logging import configure_logging


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="amor",
        description="Amor Mortuorum - A modern, dark roguelite built with Python + Arcade",
    )
    parser.add_argument(
        "--settings",
        dest="settings_path",
        type=Path,
        default=None,
        help="Path to a user settings JSON file to load/override defaults.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for new runs (default: random). Same seed reproduces the same floors.",
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="Save profile name (separate meta/run saves per profile).",
    )
    parser.add_argument(
        "--smoke",
        type=int,
        default=None,
        metavar="FRAMES",
        help="Run the game for FRAMES frames then exit (CI smoke test).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    configure_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Headless mode is opt-in via env for CI/testing. It must be configured
    # before arcade is imported, so the app import happens after this block.
    if os.environ.get("AMOR_HEADLESS") == "1":
        os.environ.setdefault("ARCADE_HEADLESS", "True")
        os.environ.setdefault("PYGLET_HEADLESS", "1")

    from .app import GameApp
    from .persistence import SaveManager

    settings = Settings.load(user_path=args.settings_path)
    save_manager = SaveManager(profile_id=args.profile)

    app = GameApp(
        settings,
        save_manager=save_manager,
        seed=args.seed,
        smoke_frames=args.smoke,
    )
    app.run()
    return 0
