from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    """Minimal GitHub REST API v3 client for issue/Epic management."""

    def __init__(self, token: str, api_base: str = "https://api.github.com") -> None:
        if not token:
            raise ValueError("GitHub token is required")
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "amor-mortuorum-epic-manager",
            }
        )

    @retry(
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(GitHubError),
        reraise=True,
    )
    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code >= 500:
            logger.warning("GitHub 5xx response: %s - %s", resp.status_code, resp.text)
            raise GitHubError(f"GitHub server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub API error {resp.status_code}: {resp.text}")
        return resp

    def _repo_url(self, repo_full: str, *parts: str) -> str:
        base = f"{self.api_base}/repos/{repo_full}"
        for p in parts:
            base += "/" + p.strip("/")
        return base

    # Search issue by title in repo
    def find_issue_by_title(self, repo_full: str, title: str) -> Optional[Dict[str, Any]]:
        # Use search endpoint
        q = f"repo:{repo_full} is:issue in:title \"{title}\""
        url = f"{self.api_base}/search/issues"
        resp = self._request("GET", url, params={"q": q, "per_page": 10})
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            if item.get("title") == title and item.get("pull_request") is None:
                return item
        return None

    def create_issue(
        self,
        repo_full: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone is not None:
            payload["milestone"] = milestone
        url = self._repo_url(repo_full, "issues")
        resp = self._request("POST", url, json=payload)
        return resp.json()

    def update_issue_body(self, repo_full: str, number: int, body: str) -> Dict[str, Any]:
        url = self._repo_url(repo_full, "issues", str(number))
        resp = self._request("PATCH", url, json={"body": body})
        return resp.json()

    def add_labels(self, repo_full: str, number: int, labels: List[str]) -> List[Dict[str, Any]]:
        url = self._repo_url(repo_full, "issues", str(number), "labels")
        resp = self._request("POST", url, json={"labels": labels})
        return resp.json()

    def create_comment(self, repo_full: str, number: int, body: str) -> Dict[str, Any]:
        url = self._repo_url(repo_full, "issues", str(number), "comments")
        resp = self._request("POST", url, json={"body": body})
        return resp.json()
