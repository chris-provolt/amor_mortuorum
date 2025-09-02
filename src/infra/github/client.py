from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class GitHubError(RuntimeError):
    """Raised when the GitHub API returns an error."""


class GitHubClient:
    """Lightweight GitHub REST v3 client for issues, labels, and comments.

    Usage:
      client = GitHubClient(token=os.environ["GITHUB_TOKEN"], repo="owner/name")
    """

    def __init__(self, token: str, repo: str, base_url: str = "https://api.github.com") -> None:
        if not token:
            raise ValueError("GitHub token must be provided")
        if not repo or "/" not in repo:
            raise ValueError("repo must be in 'owner/name' format")
        self.token = token
        self.repo = repo
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "amor-mortuorum-epic-manager/1.0",
            }
        )

    # ---------- Low-level request wrapper ----------
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        logger.debug("GitHub %s %s", method, url)
        resp = self.session.request(method=method, url=url, **kwargs)
        if resp.status_code >= 400:
            logger.error("GitHub API error %s: %s", resp.status_code, resp.text)
            raise GitHubError(f"GitHub API error {resp.status_code}: {resp.text}")
        return resp

    # ---------- Labels ----------
    def get_label(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self._request("GET", f"/repos/{self.repo}/labels/{name}")
            return resp.json()
        except GitHubError as e:
            # 404 not found
            if "404" in str(e):
                return None
            raise

    def create_label(self, name: str, color: str, description: Optional[str] = None) -> Dict[str, Any]:
        payload = {"name": name, "color": color.lstrip("#")}
        if description:
            payload["description"] = description
        resp = self._request("POST", f"/repos/{self.repo}/labels", json=payload)
        return resp.json()

    def ensure_label(self, name: str, color: str, description: Optional[str] = None) -> Dict[str, Any]:
        existing = self.get_label(name)
        if existing:
            return existing
        logger.info("Creating missing label: %s", name)
        return self.create_label(name, color, description)

    def add_labels(self, issue_number: int, labels: List[str]) -> Dict[str, Any]:
        resp = self._request(
            "POST",
            f"/repos/{self.repo}/issues/{issue_number}/labels",
            json={"labels": labels},
        )
        return resp.json()

    # ---------- Issues ----------
    def search_issue_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        # Search both open and closed issues in the repo by exact title match
        q = f'repo:{self.repo} \\"{title}\\" in:title type:issue'
        params = {"q": q, "per_page": 10}
        resp = self._request("GET", "/search/issues", params=params)
        items = resp.json().get("items", [])
        for it in items:
            if it.get("title") == title:
                # Fetch full issue to get body and labels
                num = it.get("number")
                full = self._request("GET", f"/repos/{self.repo}/issues/{num}").json()
                return full
        return None

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = self._request("POST", f"/repos/{self.repo}/issues", json=payload)
        return resp.json()

    def update_issue(self, number: int, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        resp = self._request("PATCH", f"/repos/{self.repo}/issues/{number}", json=payload)
        return resp.json()

    # ---------- Comments ----------
    def create_comment(self, issue_number: int, body: str) -> Dict[str, Any]:
        resp = self._request("POST", f"/repos/{self.repo}/issues/{issue_number}/comments", json={"body": body})
        return resp.json()
