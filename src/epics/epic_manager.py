import dataclasses
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

from .github_client import GitHubClient


@dataclass
class ChildIssueSpec:
    title: str
    body: str
    labels: List[str] = field(default_factory=list)


@dataclass
class EpicSpec:
    title: str
    summary: str
    target_window: str
    labels: List[str] = field(default_factory=lambda: ["epic"])


@dataclass
class EpicPlan:
    epic: EpicSpec
    children: List[ChildIssueSpec]


class EpicManager:
    """Creates/updates an Epic issue and its child issues from a YAML specification.

    Responsibilities:
    - Ensure 'epic' label exists (and any child labels referenced)
    - Create (or locate) the Epic issue by title
    - Create (or locate) child issues by title
    - Apply labels
    - Link child issues via comments referencing the parent epic
    - Maintain a checklist in the epic issue body reflecting child issue status
    - Idempotent: running twice should not duplicate issues
    """

    def __init__(self, client: GitHubClient, dry_run: bool = False) -> None:
        self.client = client
        self.dry_run = dry_run
        self.log = logging.getLogger(self.__class__.__name__)

    def load_plan(self, path: str) -> EpicPlan:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        epic = EpicSpec(
            title=data["epic"]["title"],
            summary=data["epic"]["summary"],
            target_window=data["epic"]["target_window"],
            labels=data["epic"].get("labels", ["epic"]),
        )
        children = [
            ChildIssueSpec(title=ci["title"], body=ci.get("body", ""), labels=ci.get("labels", []))
            for ci in data.get("children", [])
        ]
        return EpicPlan(epic=epic, children=children)

    def apply(self, plan: EpicPlan) -> Dict[str, int]:
        # Ensure labels exist
        needed_labels = set(plan.epic.labels)
        for child in plan.children:
            for lbl in child.labels:
                needed_labels.add(lbl)
        for label in sorted(needed_labels):
            self._ensure_label(label)

        # Find or create epic issue
        epic_issue = self.client.search_issue_by_title(plan.epic.title, state="open")
        if not epic_issue:
            epic_issue = self.client.search_issue_by_title(plan.epic.title, state="closed")
        if not epic_issue:
            epic_body = self._render_epic_body(plan, child_entries=[], checklist_only=False)
            epic_issue = self._create_issue(plan.epic.title, epic_body, plan.epic.labels)
        epic_number = int(epic_issue.get("number"))
        self.log.info("Epic #%s: %s", epic_number, plan.epic.title)

        # Create or find child issues
        child_refs: List[Dict[str, str]] = []
        for child in plan.children:
            found = self.client.search_issue_by_title(child.title, state="open") or self.client.search_issue_by_title(child.title, state="closed")
            if not found:
                created = self._create_issue(child.title, child.body, child.labels)
                child_number = int(created.get("number"))
                child_state = created.get("state", "open")
                # Comment with parent epic link
                self._comment_on_issue(child_number, f"Parent epic: #{epic_number}")
                child_refs.append({"number": child_number, "title": child.title, "state": child_state})
            else:
                child_number = int(found.get("number"))
                child_state = found.get("state", "open")
                child_refs.append({"number": child_number, "title": child.title, "state": child_state})
                # Optional: still add a comment linking to epic for visibility (skip duplicates for simplicity)
                self._comment_on_issue(child_number, f"Parent epic: #{epic_number}")
            # Apply labels to child (non-destructive add)
            if child.labels:
                self._add_labels_to_issue(child_number, child.labels)

        # Update Epic body with checklist
        body = self._render_epic_body(plan, child_entries=child_refs, checklist_only=False)
        self._update_issue_body(epic_number, body)

        # Ensure epic label on epic issue
        if plan.epic.labels:
            self._add_labels_to_issue(epic_number, plan.epic.labels)

        return {"epic": epic_number, "children": len(child_refs)}

    # Internal helpers with dry-run support
    def _ensure_label(self, name: str) -> None:
        self.log.debug("Ensure label: %s", name)
        if self.dry_run:
            return
        # Color can be improved via a mapping; default is GitHub's red
        self.client.ensure_label(name)

    def _create_issue(self, title: str, body: str, labels: Optional[List[str]]) -> Dict[str, any]:
        self.log.info("Create issue: %s", title)
        if self.dry_run:
            # Fabricate a minimal structure for dry-run
            return {"number": -1, "title": title, "state": "open"}
        return self.client.create_issue(title, body, labels)

    def _comment_on_issue(self, issue_number: int, body: str) -> None:
        self.log.debug("Comment on issue #%s", issue_number)
        if self.dry_run:
            return
        self.client.comment_on_issue(issue_number, body)

    def _update_issue_body(self, issue_number: int, body: str) -> None:
        self.log.debug("Update body for issue #%s", issue_number)
        if self.dry_run:
            return
        self.client.update_issue_body(issue_number, body)

    def _add_labels_to_issue(self, issue_number: int, labels: List[str]) -> None:
        self.log.debug("Add labels %s to issue #%s", labels, issue_number)
        if self.dry_run:
            return
        self.client.add_labels_to_issue(issue_number, labels)

    # Rendering
    def _render_epic_body(self, plan: EpicPlan, child_entries: List[Dict[str, any]], checklist_only: bool = False) -> str:
        """
        Renders the epic issue body including summary, goal, target window, and linked child issues as a checklist.
        """
        header = [
            f"## Summary\n{plan.epic.summary}",
            "",
            "**Goal:** Track and group related child issues under this Epic.",
            f"**Target Window:** {plan.epic.target_window}",
            "",
        ]
        checklist_lines: List[str] = ["## Linked Issues", ""]
        if not child_entries:
            checklist_lines.append("- [ ] (No child issues yet)")
        else:
            for child in child_entries:
                box = "x" if str(child.get("state", "open")) == "closed" else " "
                checklist_lines.append(f"- [{box}] #{child['number']} {child['title']}")
        checklist_lines.append("")
        labels_line = f"Labels applied: {', '.join(plan.epic.labels)}"
        parts = [] if checklist_only else header
        parts += checklist_lines
        parts += [labels_line]
        return "\n".join(parts)


def apply_epic_from_file(repo: str, config_path: str, token: Optional[str] = None, dry_run: bool = False) -> Dict[str, int]:
    """
    Convenience wrapper for CLI: applies epic from YAML file to the given repo.
    """
    # Basic logging setup if not already configured
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    client = GitHubClient(token=token, repo=repo)
    mgr = EpicManager(client, dry_run=dry_run)
    plan = mgr.load_plan(config_path)
    return mgr.apply(plan)
