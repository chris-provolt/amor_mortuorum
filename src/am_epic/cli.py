import argparse
import logging
import os
import sys
from typing import Optional

import yaml

from .epic_manager import EpicManager
from .github_client import GitHubClient, GitHubAPIError
from .models import EpicSpec


logging.basicConfig(level=os.environ.get("AM_EPIC_LOG", "INFO"))
logger = logging.getLogger("am_epic.cli")


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_apply(args: argparse.Namespace) -> int:
    token: str = args.token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("error: --token or GITHUB_TOKEN env is required", file=sys.stderr)
        return 2

    repo = args.repo or os.getenv("GITHUB_REPOSITORY")
    if not repo:
        print("error: --repo or GITHUB_REPOSITORY env is required (format: owner/name)", file=sys.stderr)
        return 2

    try:
        spec_dict = load_yaml(args.config)
        spec = EpicSpec.from_dict(spec_dict)
    except Exception as e:
        print(f"error: failed to parse config {args.config}: {e}", file=sys.stderr)
        return 2

    gh = GitHubClient(token=token, repo=repo)
    mgr = EpicManager(gh)

    try:
        result = mgr.apply(spec)
        print(f"epic={result['epic']} children={result['children']}")
        return 0
    except GitHubAPIError as e:
        logger.error("GitHub API error: %s", e)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="am-epic",
        description="Create/Update an Epic issue and its child issues in GitHub",
    )
    sub = p.add_subparsers(dest="cmd")
    apply_p = sub.add_parser("apply", help="Apply epic spec to repository")
    apply_p.add_argument("-c", "--config", required=True, help="Path to epic YAML config")
    apply_p.add_argument("--repo", help="GitHub repo in owner/name format")
    apply_p.add_argument("--token", help="GitHub token (or use GITHUB_TOKEN env)")
    apply_p.set_defaults(func=cmd_apply)
    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
