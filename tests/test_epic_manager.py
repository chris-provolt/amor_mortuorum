import io
import json
import os
from pathlib import Path

import pytest
import responses

from src.am_epic.cli import main as cli_main


@pytest.fixture()
def tmp_yaml(tmp_path: Path) -> Path:
    data = {
        "epic": {
            "title": "EPIC: Dungeon Generation & Navigation",
            "body": "Summary body\n\n<!-- epic-checklist:start --><!-- epic-checklist:end -->",
            "labels": ["epic"],
            "assignees": [],
        },
        "children": [
            {"title": "Dungeon: BSP Room Generation", "body": "BSP body", "labels": ["dungeon", "generation"]},
            {"title": "Navigation: Pathfinding & Movement", "body": "Path body", "labels": ["navigation"]},
        ],
    }
    p = tmp_path / "epic.yml"
    p.write_text(json.dumps(data))  # YAML superset; JSON is valid YAML
    return p


def _issue(number, title, body="", state="open", labels=None):
    labels = labels or []
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": l} for l in labels],
    }


@responses.activate
def test_cli_apply_creates_epic_and_children(tmp_yaml, monkeypatch):
    # Env
    monkeypatch.setenv("GITHUB_TOKEN", "tkn")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    # Label checks (GET will 404 -> create)
    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/repo/labels/epic",
        status=404,
    )
    responses.add(
        responses.POST,
        "https://api.github.com/repos/owner/repo/labels",
        json={"name": "epic"},
        status=201,
    )
    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/repo/labels/epic-child",
        status=404,
    )
    responses.add(
        responses.POST,
        "https://api.github.com/repos/owner/repo/labels",
        json={"name": "epic-child"},
        status=201,
    )

    # Search epic (none)
    responses.add(
        responses.GET,
        "https://api.github.com/search/issues?q=repo%3Aowner%2Frepo%20type%3Aissue%20in%3Atitle%20%22EPIC%3A%20Dungeon%20Generation%20%26%20Navigation%22",
        json={"items": []},
        status=200,
    )
    # Create epic
    responses.add(
        responses.POST,
        "https://api.github.com/repos/owner/repo/issues",
        json=_issue(1, "EPIC: Dungeon Generation & Navigation", "Summary body"),
        status=201,
    )

    # Children search (none)
    for title in ["Dungeon: BSP Room Generation", "Navigation: Pathfinding & Movement"]:
        url = "https://api.github.com/search/issues?q=repo%3Aowner%2Frepo%20type%3Aissue%20in%3Atitle%20%22" + requests.utils.quote(title, safe="") + "%22"
        responses.add(
            responses.GET,
            url,
            json={"items": []},
            status=200,
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/owner/repo/issues",
            json=_issue(100 + len(responses.calls), title),
            status=201,
        )

    # get_issue for building checklist (called twice: for each child once, and again when listing in comments)
    # We'll respond with the child issues created above: assume numbers 3 and 5 for simplicity
    # After the two POSTs above, we don't know exact numbers; instead, add generic matchers for GET issue
    responses.add_callback(
        responses.GET,
        responses.calls._calls is None and "" or "https://api.github.com/repos/owner/repo/issues/3",
        callback=lambda req: (200, {}, json.dumps(_issue(3, "Dungeon: BSP Room Generation"))),
    )
    responses.add_callback(
        responses.GET,
        "https://api.github.com/repos/owner/repo/issues/4",
        callback=lambda req: (200, {}, json.dumps(_issue(4, "Navigation: Pathfinding & Movement"))),
    )

    # Update epic body
    responses.add(
        responses.PATCH,
        "https://api.github.com/repos/owner/repo/issues/1",
        json=_issue(1, "EPIC: Dungeon Generation & Navigation", "updated"),
        status=200,
    )

    # Comments on epic and children
    # list comments epic -> empty
    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/repo/issues/1/comments",
        json=[],
        status=200,
    )
    # create comment epic
    responses.add(
        responses.POST,
        "https://api.github.com/repos/owner/repo/issues/1/comments",
        json={"id": 10},
        status=201,
    )

    # list comments child -> empty
    for n in [3, 4]:
        responses.add(
            responses.GET,
            f"https://api.github.com/repos/owner/repo/issues/{n}/comments",
            json=[],
            status=200,
        )
        responses.add(
            responses.POST,
            f"https://api.github.com/repos/owner/repo/issues/{n}/comments",
            json={"id": 20 + n},
            status=201,
        )

    # Run CLI
    rc = cli_main(["apply", "-c", str(tmp_yaml)])
    assert rc == 0
