import argparse
import logging
import os
import sys
from pathlib import Path

from .core.settings import Settings, user_settings_path
from .persistence.paths import default_save_root
from .utils.logging import configure_logging

logger = logging.getLogger(__name__)


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
        help="User settings JSON file (default: the one the Settings screen saves).",
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
        default=None,
        help="Save profile name (default: the profile chosen in-game, else 'default').",
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
    # A windowed (PyInstaller) build has no console: keep the log next to the saves.
    log_file = default_save_root() / "amor.log" if sys.stdout is None else None
    configure_logging(level=logging.DEBUG if args.debug else logging.INFO, log_file=log_file)

    # Headless mode is opt-in via env for CI/testing. It must be configured
    # before arcade is imported, so the app import happens after this block.
    if os.environ.get("AMOR_HEADLESS") == "1":
        os.environ.setdefault("ARCADE_HEADLESS", "True")
        os.environ.setdefault("PYGLET_HEADLESS", "1")

    from .app import GameApp
    from .persistence import SaveManager

    settings_path = args.settings_path
    if settings_path is None and user_settings_path().exists():
        settings_path = user_settings_path()
    settings = Settings.load(user_path=settings_path)
    save_manager = SaveManager(profile_id=args.profile or settings.game.profile or "default")

    app = GameApp(
        settings,
        save_manager=save_manager,
        seed=args.seed,
        smoke_frames=args.smoke,
    )
    try:
        app.run()
    except Exception:
        logger.exception("Fatal error; see the log for details")
        if sys.stdout is None:  # no console to show a traceback in
            return 1
        raise
    return 0
