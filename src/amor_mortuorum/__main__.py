from __future__ import annotations

import argparse
import logging
import os
import sys

from . import __version__
from .app import run_auto, run_gui, run_headless


def _setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="amor-mortuorum",
        description="Amor Mortuorum - MVP runner",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help="Force GUI mode (Arcade)")
    mode.add_argument("--headless", action="store_true", help="Force headless mode (console)")
    parser.add_argument("--max-steps", type=int, default=None, help="Stop after N ticks (for testing)")
    parser.add_argument("--tick-rate", type=float, default=60.0, help="Target tick rate (Hz)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity (-v, -vv)")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    # Honor CLI over env vars
    if args.gui:
        os.environ["AMOR_GUI"] = "1"
        os.environ.pop("AMOR_HEADLESS", None)
        return run_gui(max_steps=args.max_steps, tick_rate=args.tick_rate)

    if args.headless:
        os.environ["AMOR_HEADLESS"] = "1"
        os.environ.pop("AMOR_GUI", None)
        return run_headless(max_steps=args.max_steps, tick_rate=args.tick_rate)

    return run_auto(max_steps=args.max_steps, tick_rate=args.tick_rate)


if __name__ == "__main__":
    sys.exit(main())
