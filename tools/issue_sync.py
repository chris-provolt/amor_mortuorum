#!/usr/bin/env python3
"""
GitHub Issue Sync Tool for Epics and Child Issues

Purpose:
- Create/update an Epic issue with label `epic`
- Create/update child issues from a YAML config
- Link children in an Epic-managed checklist comment
- Apply labels to epic and children

Usage:
  python tools/issue_sync.py --config configs/issues/epics/ui_hud.yml --apply

Environment:
  - GITHUB_TOKEN: Personal access token or Actions token with repo scope
  - GITHUB_REPOSITORY: "owner/repo"

Dry-run:
  By default runs in dry-run mode (no API changes). Pass --apply to perform changes.

Idempotency:
  - Issues are matched by exact title within the repo.
  - A deterministic marker is embedded in issue bodies to aid identification.
  - The epic checklist comment is identified and overwritten by a hidden marker.

Tests:
  See tests/test_issue_sync.py
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests
import yaml

# Configure module-level logger
logger = logging.getLogger("issue_sync")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

GITHUB_API = "https://api.github.com"


# ---------- Data Models ----------

@dataclasses.dataclass
class IssueSpec:
    title: str
    body: str
    labels: List[str]

    def to_github_payload(self) -> Dict:
        return {"title": self.title, "body": self.body, "labels": self.labels}


@dataclasses.dataclass
class EpicSpec(IssueSpec):
    children: List[IssueSpec]


# ---------- Utility ----------

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def ensure_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Environment variable {var_name} is required")
    return value


# ---------- GitHub API Client ----------

class GitHubClient:
    def __init__(self, token: str, repo: str, dry_run: bool = True, timeout: int = 20):
        self.token = token
        self.repo = repo
        self.dry_run = dry_run
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "issue-sync-tool/1.0",
        })

    # ----- Low-level helpers -----
    def _url(self, path: str) -> str:
        return f"{GITHUB_API}{path}"

    def _request(self, method: str, path: str, **kwargs):
        url = self._url(path)
        if self.dry_run and method.upper() in {"POST", "PATCH", "PUT", "DELETE"}:
            logger.info(f"[dry-run] {method.upper()} {url} payload={kwargs.get('json')}")
            # Return a stub-like response object
            class Stub:
                status_code = 200
                def json(self):
                    return {}
            return Stub()
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if resp.status_code >= 400:
            logger.error(f"GitHub API error {resp.status_code} on {method} {url}: {resp.text}")
            raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")
        return resp

    # ----- Labels -----
    def ensure_label(self, name: str, color: str = "ededed", description: Optional[str] = None):
        path = f"/repos/{self.repo}/labels/{requests.utils.quote(name, safe='')}"
        resp = self.session.get(self._url(path), timeout=self.timeout, headers=self.session.headers)
        if resp.status_code == 200:
            logger.debug(f"Label exists: {name}")
            return
        elif resp.status_code == 404:
            payload = {"name": name, "color": color}
            if description:
                payload["description"] = description
            logger.info(f"Creating label: {name}")
            self._request("POST", f"/repos/{self.repo}/labels", json=payload)
        else:
            logger.error(f"Failed to check label {name}: {resp.status_code} {resp.text}")
            resp.raise_for_status()

    # ----- Issues -----
    def search_issue_by_title(self, title: str) -> Optional[Dict]:
        # Use search API to find exact title match
        q = f"repo:{self.repo} in:title \"{title}\""
        params = {"q": q}
        resp = self._request("GET", "/search/issues", params=params)
        data = resp.json()
        items = data.get("items", []) if isinstance(data, dict) else []
        for item in items:
            if item.get("title") == title and item.get("repository_url", "").endswith(self.repo):
                return item
        return None

    def create_issue(self, spec: IssueSpec) -> Dict:
        logger.info(f"Creating issue: {spec.title}")
        resp = self._request("POST", f"/repos/{self.repo}/issues", json=spec.to_github_payload())
        return resp.json() if hasattr(resp, "json") else {}

    def update_issue(self, number: int, spec: IssueSpec) -> Dict:
        logger.info(f"Updating issue #{number}: {spec.title}")
        resp = self._request("PATCH", f"/repos/{self.repo}/issues/{number}", json=spec.to_github_payload())
        return resp.json() if hasattr(resp, "json") else {}

    def get_issue(self, number: int) -> Dict:
        resp = self._request("GET", f"/repos/{self.repo}/issues/{number}")
        return resp.json()

    # ----- Comments -----
    def list_issue_comments(self, number: int) -> List[Dict]:
        resp = self._request("GET", f"/repos/{self.repo}/issues/{number}/comments")
        return resp.json()

    def create_comment(self, number: int, body: str) -> Dict:
        logger.info(f"Creating comment on issue #{number}")
        resp = self._request("POST", f"/repos/{self.repo}/issues/{number}/comments", json={"body": body})
        return resp.json() if hasattr(resp, "json") else {}

    def update_comment(self, comment_id: int, body: str) -> Dict:
        logger.info(f"Updating comment id {comment_id}")
        resp = self._request("PATCH", f"/repos/{self.repo}/issues/comments/{comment_id}", json={"body": body})
        return resp.json() if hasattr(resp, "json") else {}


# ---------- Builders ----------

ISSUE_MARKER_TEMPLATE = "<!-- issue-sync:{id} -->"
COMMENT_MARKER_TEMPLATE = "<!-- issue-sync:children-list:{id} -->"

LABEL_COLORS = {
    "epic": "b57fff",
    "ui": "1d76db",
    "hud": "fbca04",
    "frontend": "0052cc",
    "epic-child": "c5def5",
}


def embed_marker_in_body(body: str, marker_id: str) -> str:
    marker = ISSUE_MARKER_TEMPLATE.format(id=marker_id)
    if marker in body:
        return body
    return f"{body}\n\n{marker}\n"


def ensure_issue_labels(client: GitHubClient, labels: List[str]):
    for label in labels:
        client.ensure_label(label, color=LABEL_COLORS.get(label, "ededed"))


def format_epic_children_comment(epic_id: str, child_issues: List[Dict]) -> str:
    total = len(child_issues)
    closed = sum(1 for c in child_issues if c.get("state") == "closed")
    lines = [
        COMMENT_MARKER_TEMPLATE.format(id=epic_id),
        f"Progress: {closed}/{total} completed",
        "",
        "Child Issues:",
    ]
    for c in child_issues:
        number = c.get("number")
        title = c.get("title")
        state = c.get("state")
        checked = "x" if state == "closed" else " "
        lines.append(f"- [{checked}] #{number} {title}")
    lines.append("")
    lines.append("This checklist is managed by issue_sync.py. Do not edit manually.")
    return "\n".join(lines)


def find_managed_comment(comments: List[Dict], epic_id: str) -> Optional[Dict]:
    marker = COMMENT_MARKER_TEMPLATE.format(id=epic_id)
    for c in comments:
        if isinstance(c.get("body"), str) and marker in c.get("body"):
            return c
    return None


# ---------- Core Sync Logic ----------

def load_epic_config(path: str) -> EpicSpec:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    epic_data = data.get("epic")
    if not epic_data:
        raise ValueError("Config missing top-level 'epic' key")
    title = epic_data["title"]
    body = epic_data.get("body", "")
    labels = epic_data.get("labels", ["epic"]) or ["epic"]
    children_specs: List[IssueSpec] = []
    for c in epic_data.get("children", []):
        ct = c["title"]
        cb = c.get("body", "")
        cl = c.get("labels", ["epic-child"]) or ["epic-child"]
        children_specs.append(IssueSpec(title=ct, body=cb, labels=cl))
    return EpicSpec(title=title, body=body, labels=labels, children=children_specs)


def sync_epic_and_children(client: GitHubClient, epic: EpicSpec) -> Tuple[Dict, List[Dict]]:
    epic_marker_id = slugify(epic.title)

    # Ensure labels exist
    ensure_issue_labels(client, list(set(epic.labels + ["epic"])) )

    # Prepare epic body with marker
    epic_body = embed_marker_in_body(epic.body, epic_marker_id)

    # Find or create epic issue
    existing_epic = client.search_issue_by_title(epic.title)
    if existing_epic:
        epic_number = existing_epic["number"]
        epic_url = existing_epic.get("html_url")
        logger.info(f"Found existing epic #{epic_number}: {epic_url}")
        updated_epic = client.update_issue(epic_number, IssueSpec(title=epic.title, body=epic_body, labels=epic.labels))
        epic_issue = existing_epic if not updated_epic else {**existing_epic, **updated_epic}
    else:
        epic_issue = client.create_issue(IssueSpec(title=epic.title, body=epic_body, labels=epic.labels))
        epic_number = epic_issue.get("number")
        logger.info(f"Created epic #{epic_number}: {epic_issue.get('html_url')}")

    # Ensure child labels exist
    child_label_set = set()
    for c in epic.children:
        for l in c.labels:
            child_label_set.add(l)
    ensure_issue_labels(client, list(child_label_set))

    # Create/update children
    child_issues: List[Dict] = []
    for child in epic.children:
        # Append parent link and marker to child body
        child_marker_id = slugify(child.title)
        child_body = child.body
        child_body += f"\n\nParent Epic: #{epic_number}\n"
        child_body = embed_marker_in_body(child_body, child_marker_id)
        child_spec = IssueSpec(title=child.title, body=child_body, labels=list(set(child.labels + ["epic-child"])) )

        existing = client.search_issue_by_title(child.title)
        if existing:
            number = existing["number"]
            logger.info(f"Found existing child issue #{number}: {child.title}")
            updated = client.update_issue(number, child_spec)
            issue_obj = existing if not updated else {**existing, **updated}
        else:
            issue_obj = client.create_issue(child_spec)
            logger.info(f"Created child issue #{issue_obj.get('number')}: {child.title}")
        child_issues.append(issue_obj)

    # Build/update epic checklist comment
    comments = client.list_issue_comments(epic_issue["number"]) if epic_issue.get("number") else []
    managed = find_managed_comment(comments, epic_marker_id)

    # Retrieve latest state for children to compute progress
    resolved_children: List[Dict] = []
    for c in child_issues:
        if not c:
            continue
        num = c.get("number")
        if not num:
            continue
        full = client.get_issue(num)
        resolved_children.append(full if full else c)

    comment_body = format_epic_children_comment(epic_marker_id, resolved_children)
    if managed:
        client.update_comment(managed["id"], comment_body)
    else:
        client.create_comment(epic_issue["number"], comment_body)

    return epic_issue, resolved_children


# ---------- CLI ----------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync an Epic and child issues to GitHub")
    parser.add_argument("--config", required=True, help="Path to epic YAML config")
    parser.add_argument("--apply", action="store_true", help="Apply changes (not dry-run)")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"), help="owner/repo (default from env)")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (default from env)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.repo:
        logger.error("--repo or GITHUB_REPOSITORY must be set")
        return 2
    if not args.token:
        logger.error("--token or GITHUB_TOKEN must be set")
        return 2

    epic_spec = load_epic_config(args.config)
    client = GitHubClient(token=args.token, repo=args.repo, dry_run=not args.apply)
    try:
        sync_epic_and_children(client, epic_spec)
    except Exception as e:
        logger.exception("Failed to sync epic and children: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
