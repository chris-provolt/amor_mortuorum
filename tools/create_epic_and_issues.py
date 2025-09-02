#!/usr/bin/env python3
import argparse
import logging
import os
import sys

from amormortuorum.issue_tools.epic_generator import EpicGenerator
from amormortuorum.issue_tools.github_client import GitHubClient


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create an EPIC and its child issues from a YAML config")
    parser.add_argument("--config", required=True, help="Path to the epic YAML config")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPO"), help="GitHub repo 'owner/repo' (or set GITHUB_REPO)")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN)")
    parser.add_argument("--dry-run", action="store_true", help="Do not call GitHub; print payloads only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    if not args.repo:
        print("Error: --repo or GITHUB_REPO env var is required", file=sys.stderr)
        return 2

    if not args.token and not args.dry_run:
        print("Error: --token or GITHUB_TOKEN env var is required (unless --dry-run)", file=sys.stderr)
        return 2

    client = GitHubClient(repo=args.repo, token=args.token or "DUMMY")
    gen = EpicGenerator(client)
    cfg = gen.load_config(args.config)

    result = gen.generate(cfg, dry_run=args.dry_run)

    if args.dry_run:
        print("=== DRY RUN: Epic Payload ===")
        print(result["epic"]["title"]) 
        print("\nLabels:", result["epic"]["labels"]) 
        print("\nBody:\n", result["epic"]["body"]) 
        print("\n=== DRY RUN: Child Issues ===")
        for child in result["children"]:
            print("-", child["title"], "labels=", child["labels"]) 
        return 0

    print("Created/updated Epic #", result["epic_number"]) 
    print("Children:")
    for title, num in result["children"].items():
        print(f"- #{num}: {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
