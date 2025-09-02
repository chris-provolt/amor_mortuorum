import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class GitHubAPI:
    """Lightweight GitHub REST API client for issues and labels.

    This class only implements the endpoints needed for Epic tracking.
    It uses PAT/GITHUB_TOKEN from the environment or provided explicitly.
    """

    repo: str
    token: Optional[str] = None
    base_url: str = "https://api.github.com"

    def __post_init__(self) -> None:
        if not self.token:
            self.token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not self.repo or "/" not in self.repo:
            raise ValueError("repo must be in 'owner/name' format, got: %r" % self.repo)
        if not self.token:
            logger.warning("GitHub token not provided. Requests may be rate-limited or fail.")

    # ------------------- HTTP helpers -------------------
    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "amor-mortuorum-epics-bot/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/repos/{self.repo}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Tuple[int, Any, Dict[str, Any]]:
        url = self._url(path)
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        resp = requests.request(method, url, headers=headers, **kwargs)
        try:
            data = resp.json() if resp.text else {}
        except json.JSONDecodeError:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            logger.error("GitHub API error %s %s -> %s: %s", method, url, resp.status_code, data)
        else:
            logger.debug("GitHub API %s %s -> %s", method, url, resp.status_code)
        return resp.status_code, data, dict(resp.headers)

    # ------------------- Labels -------------------
    def ensure_label(self, name: str, color: str = "6f42c1", description: str = "") -> Dict[str, Any]:
        code, data, _ = self._request("GET", f"/labels/{name}")
        if code == 200:
            return data
        payload = {"name": name, "color": color.lstrip("#"), "description": description}
        code, data, _ = self._request("POST", "/labels", json=payload)
        if code not in (200, 201):
            raise RuntimeError(f"Failed to create label {name}: {data}")
        return data

    # ------------------- Issues -------------------
    def find_issue_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        # The GitHub search API has limitations; prefer listing open issues by pagination and match title
        # Use search API for convenience
        q = f"repo:{self.repo} type:issue in:title \"{title}\""
        code, data, _ = self._request("GET", f"/search/issues?q={requests.utils.requote_uri(q)}")
        if code != 200:
            return None
        items = data.get("items", [])
        for item in items:
            if item.get("title") == title:
                # Fetch full issue for body/labels
                return self.get_issue(item["number"]) or item
        return None

    def search_issues(self, query: str) -> List[Dict[str, Any]]:
        code, data, _ = self._request("GET", f"/search/issues?q={requests.utils.requote_uri(query)}")
        if code != 200:
            return []
        return data.get("items", [])

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        code, data, _ = self._request("POST", "/issues", json=payload)
        if code not in (200, 201):
            raise RuntimeError(f"Failed to create issue: {data}")
        return data

    def get_issue(self, number: int) -> Optional[Dict[str, Any]]:
        code, data, _ = self._request("GET", f"/issues/{number}")
        if code == 200:
            return data
        return None

    def update_issue(self, number: int, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        code, data, _ = self._request("PATCH", f"/issues/{number}", json=payload)
        if code not in (200, 201):
            raise RuntimeError(f"Failed to update issue: {data}")
        return data

    # ------------------- Comments -------------------
    def add_comment(self, issue_number: int, body: str) -> Dict[str, Any]:
        code, data, _ = self._request("POST", f"/issues/{issue_number}/comments", json={"body": body})
        if code not in (200, 201):
            raise RuntimeError(f"Failed to add comment: {data}")
        return data

    def list_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        code, data, _ = self._request("GET", f"/issues/{issue_number}/comments")
        if code != 200:
            return []
        return data

    def update_comment(self, comment_id: int, body: str) -> Dict[str, Any]:
        code, data, _ = self._request("PATCH", f"/issues/comments/{comment_id}", json={"body": body})
        if code != 200:
            raise RuntimeError(f"Failed to update comment: {data}")
        return data

    def upsert_marked_comment(self, issue_number: int, marker: str, content: str) -> Dict[str, Any]:
        """Create or update a comment that contains a unique invisible marker.

        The marker should be a short token like 'epic-child-links'. It will be
        embedded inside an HTML comment to avoid user-visible noise.
        """
        token_start = f"<!-- {marker}:start -->"
        token_end = f"<!-- {marker}:end -->"
        body = f"{token_start}\n{content}\n{token_end}"
        existing = self.list_comments(issue_number)
        for c in existing:
            if isinstance(c.get("body"), str) and token_start in c["body"] and token_end in c["body"]:
                return self.update_comment(c["id"], body)
        return self.add_comment(issue_number, body)
