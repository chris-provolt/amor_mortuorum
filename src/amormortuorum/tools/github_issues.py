import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests


logger = logging.getLogger(__name__)


class GitHubError(RuntimeError):
    """Generic error for GitHub client failures."""


@dataclass
class IssueRef:
    number: int
    title: str
    html_url: str


class GitHubClient:
    """
    Thin wrapper over GitHub REST API v3 for creating/updating issues and labels.

    Supports:
    - Creating issues
    - Updating issues
    - Searching issues by title
    - Adding labels
    - Adding comments
    - Ensuring labels existence
    - Idempotent creation: find by title first, then create if missing
    """

    def __init__(self, repo: str, token: Optional[str] = None, base_url: str = "https://api.github.com") -> None:
        if "/" not in repo:
            raise ValueError("repo must be in the form 'owner/repo'")
        self.repo = repo
        self.base_url = base_url.rstrip("/")
        token = token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token not provided. Set GITHUB_TOKEN or pass token explicitly.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "amormortuorum-epic-bot/1.0",
            }
        )

    # --------------- Labels ---------------
    def ensure_label(self, name: str, color: str = "0e8a16", description: str = "") -> None:
        """
        Ensure a label exists in the repository. Create it if absent.
        """
        url = f"{self.base_url}/repos/{self.repo}/labels/{name}"
        r = self.session.get(url)
        if r.status_code == 200:
            logger.debug("Label '%s' already exists", name)
            return
        if r.status_code != 404:
            raise GitHubError(f"Failed to get label '{name}': {r.status_code} {r.text}")
        create_url = f"{self.base_url}/repos/{self.repo}/labels"
        cr = self.session.post(create_url, json={"name": name, "color": color.lstrip('#'), "description": description})
        if cr.status_code not in (200, 201):
            raise GitHubError(f"Failed to create label '{name}': {cr.status_code} {cr.text}")
        logger.info("Created label '%s'", name)

    def add_labels(self, issue_number: int, labels: List[str]) -> None:
        if not labels:
            return
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/labels"
        r = self.session.post(url, json={"labels": labels})
        if r.status_code not in (200, 201):
            raise GitHubError(f"Failed to add labels to issue #{issue_number}: {r.status_code} {r.text}")
        logger.debug("Added labels %s to issue #%s", labels, issue_number)

    # --------------- Issues ---------------
    def search_issue_by_title(self, title: str) -> Optional[IssueRef]:
        """Search issue by exact title. Returns first exact match if any."""
        # Use search API, filter client-side for exact title match
        q = f"repo:{self.repo} is:issue in:title \"{title}\""
        url = f"{self.base_url}/search/issues"
        r = self.session.get(url, params={"q": q, "per_page": 10})
        if r.status_code != 200:
            raise GitHubError(f"Failed to search issues: {r.status_code} {r.text}")
        data = r.json()
        for item in data.get("items", []):
            if item.get("title") == title:
                return IssueRef(number=item["number"], title=item["title"], html_url=item["html_url"])
        return None

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> IssueRef:
        url = f"{self.base_url}/repos/{self.repo}/issues"
        payload: Dict = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        r = self.session.post(url, json=payload)
        if r.status_code not in (200, 201):
            raise GitHubError(f"Failed to create issue '{title}': {r.status_code} {r.text}")
        data = r.json()
        return IssueRef(number=data["number"], title=data["title"], html_url=data["html_url"])

    def update_issue(self, issue_number: int, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None, labels: Optional[List[str]] = None) -> IssueRef:
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
        payload: Dict = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        r = self.session.patch(url, json=payload)
        if r.status_code != 200:
            raise GitHubError(f"Failed to update issue #{issue_number}: {r.status_code} {r.text}")
        d = r.json()
        return IssueRef(number=d["number"], title=d["title"], html_url=d["html_url"])

    def add_comment(self, issue_number: int, body: str) -> None:
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/comments"
        r = self.session.post(url, json={"body": body})
        if r.status_code not in (200, 201):
            raise GitHubError(f"Failed to add comment to issue #{issue_number}: {r.status_code} {r.text}")


# -------------------- EPIC Utilities --------------------

AUTO_SECTION_START = "<!-- AUTO-GENERATED-CHILD-ISSUES:START -->"
AUTO_SECTION_END = "<!-- AUTO-GENERATED-CHILD-ISSUES:END -->"


def render_checklist(child_issues: List[IssueRef], completed: Optional[List[int]] = None) -> str:
    completed = set(completed or [])
    lines = ["- [x] {title} ({url})" if i.number in completed else f"- [ ] {i.title} ({i.html_url})" for i in child_issues]
    return "\n".join(lines)


def upsert_autosection(body: str, section: str) -> str:
    """
    Replace or insert the auto-generated section between markers.
    """
    pattern = re.compile(re.escape(AUTO_SECTION_START) + r"[\s\S]*?" + re.escape(AUTO_SECTION_END), re.MULTILINE)
    replacement = f"{AUTO_SECTION_START}\n{section}\n{AUTO_SECTION_END}"
    if pattern.search(body or ""):
        return pattern.sub(replacement, body)
    return (body or "") + ("\n\n" if body else "") + replacement


def ensure_epic_with_children(
    gh: GitHubClient,
    epic_title: str,
    epic_body_template: str,
    epic_labels: List[str],
    child_specs: List[Tuple[str, str, List[str]]],
) -> Tuple[IssueRef, List[IssueRef]]:
    """
    Ensure an Epic issue exists with the given children linked.

    - Ensures all labels exist and are applied to Epic.
    - Idempotently creates/updates child issues by title.
    - Updates the Epic body to include a checklist with links to the children between markers.
    - Adds a comment to the Epic summarizing the created/linked issues.
    - Adds a backlink comment to each child, pointing to the Epic.

    child_specs: List of (title, body, labels)
    Returns: (epic_issue, child_issues)
    """
    # Ensure labels exist
    for label in set(epic_labels + [l for _, _, ls in child_specs for l in ls]):
        gh.ensure_label(label)

    # Upsert epic
    existing_epic = gh.search_issue_by_title(epic_title)
    epic_body = epic_body_template
    if existing_epic is None:
        epic_issue = gh.create_issue(epic_title, epic_body, labels=list(set(epic_labels)))
        logger.info("Created Epic #%s: %s", epic_issue.number, epic_issue.title)
    else:
        # Update labels on epic as well to ensure it has 'epic'
        epic_issue = gh.update_issue(existing_epic.number, body=epic_body)
        gh.add_labels(epic_issue.number, list(set(epic_labels)))
        logger.info("Found existing Epic #%s: %s", epic_issue.number, epic_issue.title)

    # Upsert children
    child_issues: List[IssueRef] = []
    for title, body, labels in child_specs:
        existing = gh.search_issue_by_title(title)
        if existing is None:
            issue = gh.create_issue(title, body, labels=list(set(labels)))
            logger.info("Created child issue #%s: %s", issue.number, issue.title)
        else:
            issue = gh.update_issue(existing.number, body=body)
            gh.add_labels(issue.number, list(set(labels)))
            logger.info("Found existing child issue #%s: %s", issue.number, issue.title)
        child_issues.append(issue)

    # Update epic with checklist
    checklist = render_checklist(child_issues)
    updated_body = upsert_autosection(epic_body, checklist)
    gh.update_issue(epic_issue.number, body=updated_body)

    # Add comment to epic with quick links
    links = "\n".join([f"- {c.title} #{c.number} ({c.html_url})" for c in child_issues])
    gh.add_comment(
        epic_issue.number,
        (
            "Auto-generated child issues have been created/linked to this Epic.\n\n"
            f"{links}\n\n"
            "Progress is tracked via the checklist in the Epic body."
        ),
    )

    # Backlink comments on children
    for c in child_issues:
        gh.add_comment(c.number, f"Linked to Epic: {epic_issue.title} #{epic_issue.number}")

    return epic_issue, child_issues
