import copy
from typing import Any, Dict, List, Optional

import pytest

from epics.manager import EpicConfig, EpicManager, ChildIssueConfig


class FakeGitHubAPI:
    def __init__(self):
        self.repo = "owner/name"
        self.labels = {}
        self.issues: Dict[int, Dict[str, Any]] = {}
        self.comments: Dict[int, List[Dict[str, Any]]] = {}
        self._counter = 0

    # Label ops
    def ensure_label(self, name: str, color: str = "", description: str = ""):
        self.labels[name] = {"name": name, "color": color, "description": description}
        return self.labels[name]

    # Issue ops
    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def find_issue_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        for i in self.issues.values():
            if i["title"] == title:
                return copy.deepcopy(i)
        return None

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        num = self._next()
        issue = {
            "number": num,
            "title": title,
            "body": body,
            "state": "open",
            "labels": [{"name": l} for l in (labels or [])],
            "assignees": assignees or [],
        }
        self.issues[num] = issue
        self.comments[num] = []
        return copy.deepcopy(issue)

    def get_issue(self, number: int) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self.issues.get(number))

    def update_issue(self, number: int, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        issue = self.issues[number]
        if title is not None:
            issue["title"] = title
        if body is not None:
            issue["body"] = body
        if state is not None:
            issue["state"] = state
        if labels is not None:
            issue["labels"] = [{"name": l} for l in labels]
        return copy.deepcopy(issue)

    # Comments
    def add_comment(self, issue_number: int, body: str) -> Dict[str, Any]:
        cid = len(self.comments[issue_number]) + 1
        c = {"id": cid, "body": body}
        self.comments[issue_number].append(c)
        return copy.deepcopy(c)

    def list_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        return copy.deepcopy(self.comments[issue_number])

    def update_comment(self, comment_id: int, body: str) -> Dict[str, Any]:
        # find and replace
        for lst in self.comments.values():
            for c in lst:
                if c["id"] == comment_id:
                    c["body"] = body
                    return copy.deepcopy(c)
        raise KeyError(comment_id)

    def upsert_marked_comment(self, issue_number: int, marker: str, content: str) -> Dict[str, Any]:
        token_start = f"<!-- {marker}:start -->"
        token_end = f"<!-- {marker}:end -->"
        body = f"{token_start}\n{content}\n{token_end}"
        for c in self.comments[issue_number]:
            if token_start in c["body"] and token_end in c["body"]:
                return self.update_comment(c["id"], body)
        return self.add_comment(issue_number, body)


@pytest.fixture()
def api():
    return FakeGitHubAPI()


def test_sync_creates_epic_and_children(api):
    cfg = EpicConfig(
        title="EPIC: Audio & Atmosphere",
        body="Summary...",
        labels=["epic", "audio"],
        children=[
            ChildIssueConfig(title="SFX: Gameplay and UI Hooks", labels=["audio", "sfx"]),
            ChildIssueConfig(title="Ambient: Biome Loops & Transitions", labels=["audio", "ambient"]),
            ChildIssueConfig(title="Boss Music: Dynamic Layering", labels=["audio", "boss", "music"]),
        ],
    )
    manager = EpicManager(api=api)

    result = manager.sync(cfg)

    # Epic created
    epic_num = result["epic_number"]
    assert epic_num in api.issues
    epic = api.issues[epic_num]
    assert any(l["name"] == "epic" for l in epic["labels"])  # epic label applied

    # Children created and linked
    child_nums = result["child_numbers"]
    assert len(child_nums) == 3

    # Epic body has checklist
    body = epic["body"]
    assert "<!-- epic-checklist:start -->" in body
    assert "SFX: Gameplay and UI Hooks" in body

    # Epic has child links comment
    comments = api.comments[epic_num]
    assert any("<!-- epic-child-links:start -->" in c["body"] for c in comments)

    # Each child has link-back comment
    for n in child_nums:
        c_list = api.comments[n]
        assert any("<!-- linked-to-epic:start -->" in c["body"] for c in c_list)


def test_sync_is_idempotent(api):
    cfg = EpicConfig(
        title="EPIC: Audio & Atmosphere",
        body="Summary...",
        labels=["epic", "audio"],
        children=[ChildIssueConfig(title="SFX: Gameplay and UI Hooks", labels=["audio", "sfx"])],
    )
    manager = EpicManager(api=api)

    first = manager.sync(cfg)
    second = manager.sync(cfg)

    assert first["epic_number"] == second["epic_number"]
    assert first["child_numbers"] == second["child_numbers"]

    # Comments should not multiply
    epic_num = first["epic_number"]
    assert len(api.comments[epic_num]) == 1  # single upserted child-links comment


def test_checklist_marks_closed(api):
    cfg = EpicConfig(
        title="EPIC: Audio & Atmosphere",
        body="Summary...",
        labels=["epic", "audio"],
        children=[ChildIssueConfig(title="SFX: Gameplay and UI Hooks", labels=["audio", "sfx"])],
    )
    manager = EpicManager(api=api)

    result = manager.sync(cfg)
    child_num = result["child_numbers"][0]

    # Close the child, resync
    api.update_issue(child_num, state="closed")
    result2 = manager.sync(cfg)

    epic_num = result2["epic_number"]
    epic_body = api.issues[epic_num]["body"]
    assert "- [x]" in epic_body
