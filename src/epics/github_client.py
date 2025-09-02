import logging
import os
from typing import Any, Dict, List, Optional

import requests


class GitHubError(RuntimeError):
    """Raised for GitHub REST API invocation errors."""


class GitHubClient:
    """
    Thin wrapper over GitHub REST API v3 for issues management.

    Notes:
    - Uses a shared Session for connection reuse.
    - Raises GitHubError on non-2xx responses with useful context.
    - Provides minimal endpoints required for epic/child issue management.
    """

    def __init__(self, token: Optional[str], repo: str, base_url: str = "https://api.github.com") -> None:
        if not token:
            token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required. Provide via constructor or GITHUB_TOKEN env var.")
        if not repo or "/" not in repo:
            raise ValueError("repo must be in 'owner/repo' format")
        self._token = token
        self._repo = repo
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "amor-mortuorum-epic-cli/1.0",
            }
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def owner(self) -> str:
        return self._repo.split("/", 1)[0]

    @property
    def repo(self) -> str:
        return self._repo.split("/", 1)[1]

    def _url(self, path: str) -> str:
        return f"{self._base_url}/repos/{self.owner}/{self.repo}{path}"

    def _request(self, method: str, url: str, *, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> requests.Response:
        self._logger.debug("GitHub %s %s params=%s json=%s", method, url, params, json)
        resp = self._session.request(method, url, params=params, json=json, timeout=30)
        # 422 can be OK for some endpoints (e.g., creating existing labels)
        if 200 <= resp.status_code < 300:
            return resp
        if resp.status_code == 422 and url.endswith("/labels") and method.upper() == "POST":
            # Label already exists; treat as success
            self._logger.debug("Label already exists: %s", json.get("name") if json else "<unknown>")
            return resp
        # Attempt to extract useful error details
        try:
            detail = resp.json()
        except Exception:  # noqa: BLE001
            detail = resp.text
        raise GitHubError(f"GitHub API error {resp.status_code} for {method} {url}: {detail}")

    # Labels
    def ensure_label(self, name: str, color: str = "B60205", description: Optional[str] = None) -> None:
        """Ensures a label exists. Creates if missing. Idempotent.

        Uses POST and treats 422 (already exists) as success to avoid extra GETs.
        """
        payload = {"name": name, "color": color}
        if description:
            payload["description"] = description
        url = self._url("/labels")
        self._request("POST", url, json=payload)

    def add_labels_to_issue(self, issue_number: int, labels: List[str]) -> Dict[str, Any]:
        url = self._url(f"/issues/{issue_number}/labels")
        resp = self._request("POST", url, json={"labels": labels})
        return resp.json()

    # Issues
    def search_issue_by_title(self, title: str, state: str = "open") -> Optional[Dict[str, Any]]:
        """Search issues by exact title. Returns first exact match in the repository or None.
        Uses GitHub Search API.
        """
        # Example: q=repo:owner/repo+type:issue+state:open+in:title+"My Title"
        q = f"repo:{self.owner}/{self.repo} type:issue in:title \"{title}\""
        if state in {"open", "closed"}:
            q += f" state:{state}"
        url = f"{self._base_url}/search/issues"
        resp = self._request("GET", url, params={"q": q})
        data = resp.json()
        for item in data.get("items", []):
            if item.get("title") == title and item.get("repository_url", "").endswith(f"/{self.owner}/{self.repo}"):
                return item
        return None

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        url = self._url("/issues")
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = self._request("POST", url, json=payload)
        return resp.json()

    def update_issue_body(self, issue_number: int, body: str) -> Dict[str, Any]:
        url = self._url(f"/issues/{issue_number}")
        resp = self._request("PATCH", url, json={"body": body})
        return resp.json()

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        url = self._url(f"/issues/{issue_number}")
        resp = self._request("GET", url)
        return resp.json()

    def comment_on_issue(self, issue_number: int, body: str) -> Dict[str, Any]:
        url = self._url(f"/issues/{issue_number}/comments")
        resp = self._request("POST", url, json={"body": body})
        return resp.json()
