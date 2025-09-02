from __future__ import annotations

import json
import logging
import sys

from .config import build_settings, parse_args
from .game import generate_floor


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    settings = build_settings(args)
    data = generate_floor(settings, args.floor)
    # Print JSON summary so it can be diffed across runs
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
