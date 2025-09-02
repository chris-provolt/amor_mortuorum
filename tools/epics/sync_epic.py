#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from typing import Optional

from epics.github_api import GitHubAPI
from epics.manager import EpicManager, discover_epic_config_by_title, load_epic_config


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def detect_repo(repo: Optional[str]) -> str:
    if repo:
        return repo
    env_repo = os.getenv("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo
    print("Error: --repo not provided and GITHUB_REPOSITORY not set", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync a GitHub Epic and its child issues from a YAML config.")
    parser.add_argument("--repo", help="GitHub repo in owner/name format (default: $GITHUB_REPOSITORY)")
    parser.add_argument("--config", help="Path to epic YAML config. If omitted, will attempt to infer from an epic issue title via --epic-number.")
    parser.add_argument("--epic-number", type=int, help="Epic issue number to infer config by title, if --config not supplied.")
    parser.add_argument("--configs-dir", default="configs/epics", help="Directory to search for configs when inferring by title.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    repo = detect_repo(args.repo)
    api = GitHubAPI(repo=repo)

    config_path = args.config
    if not config_path:
        if not args.epic_number:
            print("Error: Either --config or --epic-number is required", file=sys.stderr)
            return 2
        epic = api.get_issue(args.epic_number)
        if not epic:
            print(f"Error: Epic issue #{args.epic_number} not found", file=sys.stderr)
            return 2
        title = epic.get("title") or ""
        config_path = discover_epic_config_by_title(args.configs_dir, title)
        if not config_path:
            print(f"Error: No epic config found in {args.configs_dir} matching title: {title}", file=sys.stderr)
            return 2

    cfg = load_epic_config(config_path)
    manager = EpicManager(api=api)
    result = manager.sync(cfg)
    logging.info("Synced Epic #%s with %d children", result["epic_number"], len(result["child_numbers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
