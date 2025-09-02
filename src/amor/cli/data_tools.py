from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from ..data.loader import DataLoader, DataValidationError
from ..tools.tiled_prefab import TiledPrefabLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _cmd_validate(args: argparse.Namespace) -> int:
    loader = DataLoader()

    paths = []
    root = Path(args.path)
    if root.is_dir():
        paths = list(root.rglob("*.json"))
    else:
        paths = [root]

    success = True
    for p in paths:
        try:
            data = loader.load(p, validate=args.validate, schema=args.schema)
            print(f"OK: {p}")
        except DataValidationError as e:
            success = False
            print(f"INVALID: {p}\n{e.to_human()}\n")
        except Exception as e:  # pragma: no cover - CLI convenience
            success = False
            print(f"ERROR: {p}: {e}")

    return 0 if success else 1


def _cmd_tiled_prefabs(args: argparse.Namespace) -> int:
    tool = TiledPrefabLoader()
    instances = tool.run_cli_extract(args.map, args.prefabs)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(instances, fh, indent=2)
    else:
        print(json.dumps(instances, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="amor-data", description="Amor Mortuorum data tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate JSON files against schemas")
    v.add_argument("path", help="Path to a JSON file or a directory to scan")
    v.add_argument("--schema", help="Explicit schema name or URI", default=None)
    v.add_argument("--no-validate", dest="validate", action="store_false", help="Disable validation (load only)")
    v.set_defaults(func=_cmd_validate, validate=True)

    t = sub.add_parser("tiled-prefabs", help="Extract prefab instances from a Tiled JSON map")
    t.add_argument("map", help="Path to Tiled map (JSON)")
    t.add_argument("prefabs", help="Path to prefab definitions JSON")
    t.add_argument("--out", help="Optional output file (JSON)")
    t.set_defaults(func=_cmd_tiled_prefabs)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
