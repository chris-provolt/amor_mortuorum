import os
import json
import sys
from pathlib import Path

import pytest
import responses

# Ensure the tools package is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.issue_sync import GitHubClient, load_epic_config, sync_epic_and_children, format_epic_children_comment


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")


def _search_issues_response(items):
    return {
        "total_count": len(items),
        "items": items,
    }


@responses.activate
def test_sync_creates_epic_and_children(tmp_path):
    repo = os.environ["GITHUB_REPOSITORY"]

    # Load config
    config_path = ROOT / "configs/issues/epics/ui_hud.yml"
    epic = load_epic_config(str(config_path))

    # Mock label GET 404 then POST create
    label_names = set(epic.labels)
    for child in epic.children:
        label_names.update(child.labels)
    for name in label_names:
        responses.add(
            responses.GET,
            f"https://api.github.com/repos/{repo}/labels/{name}",
            status=404,
        )
        responses.add(
            responses.POST,
            f"https://api.github.com/repos/{repo}/labels",
            json={"name": name}, status=201,
        )

    # Search epic -> none
    responses.add(
        responses.GET,
        "https://api.github.com/search/issues",
        json=_search_issues_response([]),
        status=200,
    )

    # Create epic
    epic_number = 101
    responses.add(
        responses.POST,
        f"https://api.github.com/repos/{repo}/issues",
        json={"number": epic_number, "html_url": f"https://github.com/{repo}/issues/{epic_number}", "title": epic.title, "state": "open"},
        status=201,
    )

    # For each child: search none then create
    child_numbers = []
    for idx, child in enumerate(epic.children, start=1):
        # Search
        responses.add(
            responses.GET,
            "https://api.github.com/search/issues",
            json=_search_issues_response([]),
            status=200,
        )
        # Create child
        num = 200 + idx
        child_numbers.append(num)
        responses.add(
            responses.POST,
            f"https://api.github.com/repos/{repo}/issues",
            json={"number": num, "html_url": f"https://github.com/{repo}/issues/{num}", "title": child.title, "state": "open"},
            status=201,
        )
        # GET child to compute state
        responses.add(
            responses.GET,
            f"https://api.github.com/repos/{repo}/issues/{num}",
            json={"number": num, "title": child.title, "state": "open"},
            status=200,
        )

    # No existing comments on epic
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{repo}/issues/{epic_number}/comments",
        json=[], status=200,
    )

    # Create comment
    created_comment_id = 5555
    responses.add(
        responses.POST,
        f"https://api.github.com/repos/{repo}/issues/{epic_number}/comments",
        json={"id": created_comment_id}, status=201,
    )

    client = GitHubClient(token=os.environ["GITHUB_TOKEN"], repo=repo, dry_run=False)
    epic_issue, children = sync_epic_and_children(client, epic)

    # Assertions
    assert epic_issue["number"] == epic_number
    assert len(children) == len(epic.children)

    # Verify last POST body for comment contains checklist with child issue references
    sent_requests = [c for c in responses.calls if c.request.method == "POST" and c.request.url.endswith("/comments")]
    assert sent_requests, "Expected a comment creation call"
    body = json.loads(sent_requests[-1].request.body.decode("utf-8"))
    text = body["body"]
    # Ensure it includes all child issue numbers and titles
    for num, child in zip(child_numbers, epic.children):
        assert f"#{num} {child.title}" in text
    # Ensure marker is present
    assert "<!-- issue-sync:children-list:" in text


@responses.activate
def test_checklist_formatting_marks_closed():
    epic_id = "epic-ui-hud"
    children = [
        {"number": 1, "title": "A", "state": "open"},
        {"number": 2, "title": "B", "state": "closed"},
    ]
    comment = format_epic_children_comment(epic_id, children)
    assert "Progress: 1/2" in comment
    assert "- [ ] #1 A" in comment
    assert "- [x] #2 B" in comment
