import logging
import time
from typing import Dict, List, Optional

import requests


class GitHubError(RuntimeError):
    """Raised when a GitHub API call fails."""


class GitHubClient:
    """Minimal GitHub REST API client focused on labels, issues, and comments.

    Usage:
        client = GitHubClient(repo="owner/repo", token="...")
        client.ensure_label("epic", color="5319e7", description="Epic tracker")
        issue = client.create_issue(title="My issue", body="desc", labels=["epic"]) 
        client.comment_on_issue(issue["number"], "Linked to epic #123")
    """

    API_BASE = "https://api.github.com"

    def __init__(self, repo: str, token: str, user_agent: str = "amormortuorum-epic-tool/1.0") -> None:
        if not repo or "/" not in repo:
            raise ValueError("repo must be of the form 'owner/repo'")
        if not token:
            raise ValueError("A GitHub token is required")
        self.repo = repo
        self._token = token
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": user_agent,
            }
        )
        self._labels_cache: Optional[Dict[str, Dict]] = None
        self._log = logging.getLogger(self.__class__.__name__)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.API_BASE}{path}"
        for attempt in range(3):
            resp = self._session.request(method, url, timeout=30, **kwargs)
            # Handle rate limiting gracefully
            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = resp.headers.get("X-RateLimit-Reset")
                now = time.time()
                sleep_for = max(0.0, float(reset) - now + 1.0) if reset else 5.0
                self._log.warning("Rate limit hit. Sleeping for %.2fs", sleep_for)
                time.sleep(sleep_for)
                continue
            return resp
        return resp

    def _raise_for_status(self, resp: requests.Response, context: str) -> None:
        if 200 <= resp.status_code < 300:
            return
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text}
        raise GitHubError(f"GitHub API {context} failed: {resp.status_code} {data}")

    def list_labels(self) -> Dict[str, Dict]:
        """Return a mapping of label name (lower) -> label object."""
        if self._labels_cache is not None:
            return self._labels_cache
        labels: Dict[str, Dict] = {}
        page = 1
        while True:
            resp = self._request("GET", f"/repos/{self.repo}/labels", params={"per_page": 100, "page": page})
            self._raise_for_status(resp, "list labels")
            items = resp.json()
            if not items:
                break
            for it in items:
                labels[it["name"].lower()] = it
            page += 1
        self._labels_cache = labels
        return labels

    def ensure_label(self, name: str, color: str = "5319e7", description: Optional[str] = None) -> Dict:
        """Ensure a label exists by name; create if missing.

        Returns the label object.
        """
        labels = self.list_labels()
        key = name.lower()
        if key in labels:
            return labels[key]
        payload = {"name": name, "color": color}
        if description:
            payload["description"] = description
        resp = self._request("POST", f"/repos/{self.repo}/labels", json=payload)
        if resp.status_code == 422:
            # Could be a race or color conflict; refresh cache
            self._labels_cache = None
            return self.ensure_label(name, color, description)
        self._raise_for_status(resp, f"ensure label {name}")
        self._labels_cache = None
        created = resp.json()
        return created

    def search_issue_by_title(self, title: str) -> Optional[Dict]:
        """Search issues by exact title within the repo. Return the first exact match or None.
        Note: Uses GitHub Search API which is eventually consistent; may need retries in practice.
        """
        q = f"repo:{self.repo} type:issue in:title \"{title}\""
        resp = self._request("GET", "/search/issues", params={"q": q})
        self._raise_for_status(resp, "search issues")
        items = resp.json().get("items", [])
        for it in items:
            if it.get("title") == title:
                return it
        return None

    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict:
        payload: Dict = {"title": title}
        if body is not None:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone is not None:
            payload["milestone"] = milestone
        resp = self._request("POST", f"/repos/{self.repo}/issues", json=payload)
        self._raise_for_status(resp, f"create issue '{title}'")
        return resp.json()

    def update_issue(self, number: int, body: Optional[str] = None, title: Optional[str] = None, state: Optional[str] = None) -> Dict:
        payload: Dict = {}
        if body is not None:
            payload["body"] = body
        if title is not None:
            payload["title"] = title
        if state is not None:
            payload["state"] = state
        resp = self._request("PATCH", f"/repos/{self.repo}/issues/{number}", json=payload)
        self._raise_for_status(resp, f"update issue #{number}")
        return resp.json()

    def comment_on_issue(self, number: int, body: str) -> Dict:
        payload = {"body": body}
        resp = self._request("POST", f"/repos/{self.repo}/issues/{number}/comments", json=payload)
        self._raise_for_status(resp, f"comment on issue #{number}")
        return resp.json()
