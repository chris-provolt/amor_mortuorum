import argparse
import logging
import os

from amormortuorum.tools.github_issues import GitHubClient
from amormortuorum.epics.perf_stability import create_or_update_epic


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the Performance & Stability Epic and child issues.")
    parser.add_argument("--repo", required=True, help="GitHub repository in the form 'owner/repo'")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN)")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    gh = GitHubClient(repo=args.repo, token=args.token)
    create_or_update_epic(gh)


if __name__ == "__main__":
    main()
