import argparse
import logging
import os
from pathlib import Path

from .app import GameApp
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
        help="Path to a user settings YAML file to load/override defaults.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    configure_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Make headless mode opt-in via env for CI/testing, not default in normal runs.
    if os.environ.get("AMOR_HEADLESS") == "1":
        os.environ.setdefault("PYGLET_HEADLESS", "1")

    settings = Settings.load(user_path=args.settings_path)

    app = GameApp(settings)
    app.run()
    return 0
