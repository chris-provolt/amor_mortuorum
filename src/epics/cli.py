import argparse
import json
import os
import sys

from .epic_manager import apply_epic_from_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Manage GitHub Epic and child issues from a YAML spec.")
    parser.add_argument("--repo", required=True, help="GitHub repository in 'owner/repo' format")
    parser.add_argument("--config", required=True, help="Path to Epic YAML configuration file")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Do not change GitHub, just simulate and log")
    parser.add_argument("--json", action="store_true", help="Print JSON result of apply")

    args = parser.parse_args(argv)

    try:
        result = apply_epic_from_file(repo=args.repo, config_path=args.config, token=args.token, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(result))
        else:
            print(f"Epic applied: {result}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
