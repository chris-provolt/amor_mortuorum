import json
import re
import os

import responses

from src.pm.github_client import GitHubClient
from src.pm.epic_manager import EpicManager
from src.pm.models import RepoRef, EpicConfig


@responses.activate
def test_epic_creation_and_children(tmp_path):
    # Arrange
    token = "test-token"
    os.environ["GITHUB_TOKEN"] = token
    gh = GitHubClient(token)
    repo = RepoRef(owner="octo", name="amr")
    mgr = EpicManager(gh, repo)

    # Mock search: no existing epic or children
    responses.add(
        responses.GET,
        re.compile(r"https://api\.github\.com/search/issues.*"),
        json={"total_count": 0, "items": []},
        status=200,
    )

    # Issue creation callback to increment numbers
    issue_counter = {"n": 100}

    def create_issue_cb(req):
        payload = json.loads(req.body.decode("utf-8"))
        issue_counter["n"] += 1
        body = {
            "number": issue_counter["n"],
            "title": payload.get("title"),
            "body": payload.get("body", ""),
            "labels": [{"name": l} for l in payload.get("labels", [])],
        }
        return (201, {}, json.dumps(body))

    responses.add_callback(
        responses.POST,
        "https://api.github.com/repos/octo/amr/issues",
        callback=create_issue_cb,
        content_type="application/json",
    )

    # Add labels endpoint
    responses.add(
        responses.POST,
        re.compile(r"https://api\.github\.com/repos/octo/amr/issues/\d+/labels"),
        json=[],
        status=200,
    )

    # Update epic body
    captured_patch_bodies = []

    def patch_issue_cb(req):
        payload = json.loads(req.body.decode("utf-8"))
        captured_patch_bodies.append(payload.get("body", ""))
        return (200, {}, json.dumps({"ok": True}))

    responses.add_callback(
        responses.PATCH,
        re.compile(r"https://api\.github\.com/repos/octo/amr/issues/\d+"),
        callback=patch_issue_cb,
        content_type="application/json",
    )

    # Comments endpoint
    responses.add(
        responses.POST,
        re.compile(r"https://api\.github\.com/repos/octo/amr/issues/\d+/comments"),
        json={"ok": True},
        status=201,
    )

    # Load example config from repo file shipped with the codebase
    from pathlib import Path
    cfg_path = Path("configs/epics/loot_items_economy.yml")
    assert cfg_path.exists(), "Expected epic config file to exist"

    # Act
    epic_num, children = mgr.run_from_file(str(cfg_path))

    # Assert
    assert isinstance(epic_num, int) and epic_num > 0
    # Expect at least 10+ child issues
    assert len(children) >= 10
    # Ensure epic body was updated with checklist referencing child issues (#<num>)
    assert captured_patch_bodies, "Epic body update (PATCH) should have been called"
    patched = captured_patch_bodies[-1]
    # Should include a checklist header and some issue references
    assert "Linked Issues Checklist" in patched
    assert any(re.search(r"- \[ \] #\d+", patched) for _ in [0]), patched
