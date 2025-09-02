from __future__ import annotations

import argparse
import logging
import os
from typing import Dict, List, Tuple

import yaml

from .github_client import GitHubClient
from .models import ChildIssue, EpicConfig, RepoRef

logger = logging.getLogger(__name__)


class EpicManager:
    """Creates/updates an Epic issue and its child issues, linking them together.

    Responsibilities:
    - Ensure an Epic issue exists with the 'epic' label
    - Ensure each configured child issue exists with requested labels
    - Update Epic body with a checklist of linked child issues
    - Add a comment on the Epic listing the children (for quick navigation)
    """

    def __init__(self, gh: GitHubClient, repo: RepoRef, dry_run: bool = False) -> None:
        self.gh = gh
        self.repo = repo
        self.dry_run = dry_run

    def run_from_file(self, config_path: str) -> Tuple[int, Dict[str, int]]:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cfg = EpicConfig.model_validate(data)
        return self.create_or_update_epic(cfg)

    def create_or_update_epic(self, cfg: EpicConfig) -> Tuple[int, Dict[str, int]]:
        repo_full = self.repo.full()

        # 1) Ensure Epic issue exists
        existing_epic = self.gh.find_issue_by_title(repo_full, cfg.epic_title)
        if existing_epic:
            epic_number = int(existing_epic["number"])
            logger.info("Found existing Epic #%s: %s", epic_number, cfg.epic_title)
        else:
            logger.info("Creating new Epic: %s", cfg.epic_title)
            if self.dry_run:
                epic_number = -1
            else:
                created = self.gh.create_issue(repo_full, cfg.epic_title, body=cfg.epic_body, labels=cfg.labels)
                epic_number = int(created["number"])

        # Always ensure Epic has 'epic' label applied
        if not self.dry_run:
            try:
                self.gh.add_labels(repo_full, epic_number, list(set(cfg.labels + ["epic"])))
            except Exception as e:
                logger.warning("Failed to add labels to epic #%s: %s", epic_number, e)

        # 2) Ensure each child issue exists
        child_map: Dict[str, int] = {}
        created_children: List[Tuple[str, int]] = []
        for child in cfg.children:
            labels = list(set((child.labels or []) + ["epic-child"]))
            existing = self.gh.find_issue_by_title(repo_full, child.title)
            if existing:
                number = int(existing["number"])
                logger.info("Found existing child #%s: %s", number, child.title)
            else:
                if self.dry_run:
                    number = -1
                else:
                    logger.info("Creating child issue: %s", child.title)
                    created = self.gh.create_issue(
                        repo_full,
                        title=child.title,
                        body=child.body,
                        labels=labels,
                        assignees=child.assignees,
                    )
                    number = int(created["number"])
            child_map[child.title] = number
            created_children.append((child.title, number))

        # 3) Update Epic body with checklist, and add a comment
        checklist = self._render_checklist(created_children)
        epic_body = self._merge_epic_body(cfg.epic_body, checklist)

        if not self.dry_run and epic_number > 0:
            self.gh.update_issue_body(repo_full, epic_number, epic_body)
            comment_body = self._render_comment(created_children)
            self.gh.create_comment(repo_full, epic_number, comment_body)

        return epic_number, child_map

    @staticmethod
    def _render_checklist(children: List[Tuple[str, int]]) -> str:
        lines = [
            "\n---\n",
            "### Linked Issues Checklist",
        ]
        for title, number in children:
            issue_link = f"#{number}" if number > 0 else title
            lines.append(f"- [ ] {issue_link} — {title}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _merge_epic_body(base_body: str, checklist: str) -> str:
        base_body = (base_body or "").rstrip() + "\n"
        return base_body + checklist

    @staticmethod
    def _render_comment(children: List[Tuple[str, int]]) -> str:
        lines = [
            "Linked child issues created/updated:",
        ]
        for title, number in children:
            if number > 0:
                lines.append(f"- #{number} — {title}")
            else:
                lines.append(f"- {title}")
        return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Create/Update an Epic and its child issues in GitHub")
    parser.add_argument("repo", help="GitHub repo in form owner/name")
    parser.add_argument("config", help="Path to Epic YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform write operations")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token and not args.dry_run:
        raise SystemExit("GITHUB_TOKEN environment variable is required (unless --dry-run)")

    gh = GitHubClient(token=token or "DUMMY")
    repo = RepoRef.from_full(args.repo)
    mgr = EpicManager(gh, repo, dry_run=args.dry_run)
    epic_num, children = mgr.run_from_file(args.config)
    print(f"Epic #{epic_num} processed. Children: {children}")


if __name__ == "__main__":
    main()
