import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GitHubAPIError(RuntimeError):
    """Raised for GitHub API related errors."""


class GitHubClient:
    """
    Minimal GitHub REST API v3 client for issues/labels/comments operations.

    This client intentionally avoids external heavy dependencies and provides
    clear error messages/logging. It is designed to be testable via HTTP mockers.
    """

    def __init__(self, token: str, repo: str, api_url: str = "https://api.github.com") -> None:
        if not token:
            raise ValueError("GitHub token is required")
        if not repo or "/" not in repo:
            raise ValueError("Repo must be in 'owner/name' format")
        self.token = token
        self.owner, self.repo = repo.split("/", 1)
        self.base_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "am-epic-bot/1.0"
        })

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
        except requests.RequestException as e:
            logger.exception("GitHub request failed: %s %s", method, url)
            raise GitHubAPIError(str(e)) from e
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = {"message": resp.text}
            msg = f"GitHub API error {resp.status_code} for {method} {url}: {detail}"
            logger.error(msg)
            raise GitHubAPIError(msg)
        return resp

    # Labels
    def get_label(self, name: str) -> Optional[Dict[str, Any]]:
        resp = self.session.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/labels/{name}", timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
        return None

    def ensure_label(
        self,
        name: str,
        color: str = "b60205",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ensure a label exists; create if missing."""
        label = self.get_label(name)
        if label:
            logger.debug("Label '%s' exists", name)
            return label
        payload = {"name": name, "color": color}
        if description:
            payload["description"] = description
        logger.info("Creating label '%s'", name)
        resp = self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/labels",
            json=payload,
        )
        return resp.json()

    # Issues
    def search_issue_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Try to find an issue by exact title match using search API.
        Returns first exact match if found (state can be open/closed).
        """
        from urllib.parse import quote

        q = f"repo:{self.owner}/{self.repo} type:issue in:title \"{title}\""
        resp = self._request("GET", f"/search/issues?q={quote(q, safe='')}")
        items = resp.json().get("items", [])
        expected_title = title.strip()
        for it in items:
            current = it.get("title", "").strip()
            if current == expected_title:
                # Fetch full issue to get fields like labels array with objects
                num = it.get("number")
                return self.get_issue(num)
        return None

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        logger.info("Creating issue '%s'", title)
        resp = self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues",
            json=payload,
        )
        return resp.json()

    def update_issue(
        self,
        number: int,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        logger.debug("Updating issue #%s", number)
        resp = self._request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/{number}",
            json=payload,
        )
        return resp.json()

    def add_labels(self, number: int, labels: List[str]) -> List[Dict[str, Any]]:
        logger.debug("Adding labels %s to issue #%s", labels, number)
        resp = self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues/{number}/labels",
            json={"labels": labels},
        )
        return resp.json()

    def get_issue(self, number: int) -> Dict[str, Any]:
        resp = self._request("GET", f"/repos/{self.owner}/{self.repo}/issues/{number}")
        return resp.json()

    # Comments
    def list_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        resp = self._request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
        )
        return resp.json()

    def create_comment(self, issue_number: int, body: str) -> Dict[str, Any]:
        resp = self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return resp.json()

    def update_comment(self, comment_id: int, body: str) -> Dict[str, Any]:
        resp = self._request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}",
            json={"body": body},
        )
        return resp.json()
