from __future__ import annotations

import argparse
import logging
import os
import sys

from src.infra.github.client import GitHubClient
from src.infra.github.epic import (
    EpicConfig,
    load_epic_config,
    upsert_epic_with_children,
)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Create/update an Epic and its child issues on GitHub")
    p.add_argument("--repo", required=True, help="GitHub repository in 'owner/name' format")
    p.add_argument("--config", required=True, help="Path to epic YAML configuration file")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token or set GITHUB_TOKEN env var")
    p.add_argument("--dry-run", action="store_true", help="Do not call GitHub; print actions only")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    if not args.token and not args.dry_run:
        print("Error: GitHub token required (use --token or set GITHUB_TOKEN)", file=sys.stderr)
        return 2

    try:
        epic_cfg: EpicConfig = load_epic_config(args.config)
    except Exception as e:
        logging.error("Failed to load epic config: %s", e)
        return 2

    client = GitHubClient(token=args.token or "DUMMY", repo=args.repo)
    epic_issue, children = upsert_epic_with_children(client, epic_cfg, dry_run=args.dry_run)

    # Print a small summary for CI logs
    print(f"Epic: {epic_issue.get('title')} #{epic_issue.get('number')}")
    for c in children:
        print(f"Child: {c.get('title')} #{c.get('number')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
