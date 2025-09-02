import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests


logger = logging.getLogger(__name__)


class GitHubAPIError(RuntimeError):
    """Exception for GitHub API failures."""


class GitHubAPI:
    """
    Lightweight wrapper around the GitHub REST API for repository issues and labels.

    Attributes:
        owner: Repository owner (org or user)
        repo: Repository name
        base_url: Base API URL, defaults to https://api.github.com
        session: requests.Session configured with auth headers
    """

    def __init__(self, repo: str, token: str, api_url: str = "https://api.github.com") -> None:
        if "/" not in repo:
            raise ValueError("repo must be in 'owner/repo' format")
        owner, name = repo.split("/", 1)
        self.owner = owner
        self.repo = name
        self.base_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "amor-mortuorum-epic-manager"
        })

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        logger.debug("GitHub %s %s", method, url)
        if "json" in kwargs:
            logger.debug("Payload: %s", json.dumps(kwargs["json"], indent=2))
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            logger.error("GitHub API error: %s %s -> %s", method, url, data)
            raise GitHubAPIError(f"GitHub API {method} {url} failed: {resp.status_code} {data}")
        return resp

    def ensure_label(self, name: str, color: str = "6f42c1", description: Optional[str] = None) -> Dict[str, Any]:
        """
        Ensure a label exists (create if missing).
        Defaults to a purple-ish color suitable for epics. For general labels, caller can override color.
        """
        # GET /repos/{owner}/{repo}/labels/{name}
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/labels/{quote(name, safe='')}"
        resp = self.session.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code != 404:
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            raise GitHubAPIError(f"GitHub API GET {url} failed: {resp.status_code} {data}")
        # Create label
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/labels"
        payload = {"name": name, "color": color}
        if description:
            payload["description"] = description
        resp = self._request("POST", url, json=payload)
        return resp.json()

    def add_labels(self, issue_number: int, labels: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}/labels"
        resp = self._request("POST", url, json={"labels": labels})
        return resp.json()

    def search_issue_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for an issue by exact title using GitHub search API. Returns the most relevant match if titles match exactly
        (case-sensitive). Returns None if not found.
        """
        q = f"repo:{self.owner}/{self.repo} type:issue in:title \"{title}\""
        url = f"{self.base_url}/search/issues"
        resp = self._request("GET", url, params={"q": q, "per_page": 10})
        data = resp.json()
        items = data.get("items", [])
        for it in items:
            if it.get("title") == title and not it.get("pull_request"):
                # Fetch full issue to get more fields if needed
                num = it.get("number")
                return self.get_issue(num)
        return None

    def get_issue(self, number: int) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{number}"
        resp = self._request("GET", url)
        return resp.json()

    def create_issue(self, title: str, body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        payload: Dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        resp = self._request("POST", url, json=payload)
        return resp.json()

    def update_issue(self, number: int, title: Optional[str] = None, body: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{number}"
        payload: Dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if labels is not None:
            payload["labels"] = labels
        resp = self._request("PATCH", url, json=payload)
        return resp.json()

    def comment_issue(self, number: int, body: str) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{number}/comments"
        resp = self._request("POST", url, json={"body": body})
        return resp.json()

    @staticmethod
    def sanitize_label_color(name: str) -> str:
        """
        Deterministic color for non-epic labels if caller wants some variety.
        Returns a 6-hex string without '#'.
        """
        # Create a pseudo hash to pick a color tint
        h = sum(ord(c) for c in name) % 360
        # Convert H to a simple hex based on banking ranges to keep colors readable
        # Use a pastel-like lightness
        r = int((abs((h / 60) % 2 - 1)) * 64 + 160)
        g = int(((h % 120) / 120) * 64 + 160)
        b = 200
        return f"{r:02x}{g:02x}{b:02x}"
