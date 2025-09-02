import json
import re
from pathlib import Path

import pytest
import responses

from src.epic_manager.epic_tool import orchestrate_epic


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    content = {
        "epic": {
            "title": "EPIC: Encounters & Overworld → Combat",
            "description": "Encounter triggers, enemy formations by tier, miniboss gates.",
            "target_window": "2025-08-26 → (Ongoing)",
            "labels": ["epic"],
        },
        "children": [
            {"title": "Encounter Triggers (Overworld)", "description": "Impl", "labels": ["encounters", "overworld", "combat"]},
            {"title": "Enemy Formations by Tier", "description": "Impl", "labels": ["data", "combat"]},
            {"title": "Miniboss Gates (20/40/60/80)", "description": "Impl", "labels": ["boss", "overworld", "combat"]},
        ],
    }
    p = tmp_path / "epic.yaml"
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


def _api_url(path: str) -> str:
    return f"https://api.github.com{path}"


@responses.activate
def test_orchestrate_epic_creates_epic_and_children(config_file: Path):
    repo = "owner/repo"
    token = "ghs_xxx"

    # Ensure epic label
    responses.add(
        responses.GET,
        _api_url("/repos/owner/repo/labels/epic"),
        status=404,
        json={"message": "Not Found"},
    )
    responses.add(
        responses.POST,
        _api_url("/repos/owner/repo/labels"),
        status=201,
        json={"name": "epic"},
    )

    # Ensure child labels (encounters, overworld, combat, data, boss)
    for label in ["encounters", "overworld", "combat", "data", "boss"]:
        responses.add(
            responses.GET,
            _api_url(f"/repos/owner/repo/labels/{label}"),
            status=404,
            json={"message": "Not Found"},
        )
        responses.add(
            responses.POST,
            _api_url("/repos/owner/repo/labels"),
            status=201,
            json={"name": label},
        )

    # Search children by title -> none found
    def search_query_matcher(request):
        assert request.params
        assert request.params.get("q")
        return (200, {}, json.dumps({"items": []}))

    responses.add_callback(
        responses.GET,
        _api_url("/search/issues"),
        callback=search_query_matcher,
        content_type="application/json",
    )

    # Create child issues -> return numbers
    child_titles = [
        "Encounter Triggers (Overworld)",
        "Enemy Formations by Tier",
        "Miniboss Gates (20/40/60/80)",
    ]
    child_numbers = [101, 102, 103]
    created_children_bodies = []

    def create_issue_callback(request):
        payload = json.loads(request.body)
        created_children_bodies.append(payload)
        title = payload["title"]
        idx = child_titles.index(title) if title in child_titles else -1
        # If not a child, it's the epic creation which we handle later
        if idx >= 0:
            return (201, {}, json.dumps({"number": child_numbers[idx], "title": title}))
        # Epic creation fallback
        return (201, {}, json.dumps({"number": 200, "title": payload["title"], "body": payload.get("body", "")}))

    responses.add_callback(
        responses.POST,
        _api_url("/repos/owner/repo/issues"),
        callback=create_issue_callback,
        content_type="application/json",
    )

    # Search epic by title -> none
    responses.add_callback(
        responses.GET,
        _api_url("/search/issues"),
        callback=search_query_matcher,
        content_type="application/json",
    )

    # Comment on each child, then on epic
    for _ in range(3):
        responses.add(
            responses.POST,
            re.compile(r"https://api\.github\.com/repos/owner/repo/issues/\d+/comments"),
            status=201,
            json={"id": 1},
        )
    # Epic comment
    responses.add(
        responses.POST,
        re.compile(r"https://api\.github\.com/repos/owner/repo/issues/\d+/comments"),
        status=201,
        json={"id": 2},
    )

    result = orchestrate_epic(repo=repo, token=token, config_path=str(config_file))

    # Validate result structure
    assert result["epic_number"] == 200
    assert len(result["children"]) == 3
    assert sorted([c["number"] for c in result["children"]]) == child_numbers

    # Ensure child issues created with labels
    for body in created_children_bodies:
        assert body["title"] in child_titles
        assert "labels" in body and body["labels"]

    # Validate epic creation call contained checklist with issue numbers
    # Last POST to /issues corresponds to epic creation; captured by callback
    # Instead, we can inspect that at least one of the comments used the epic number and child references
    # But better: add an assertion that a request with body containing '- [ ] #101' was made
    post_requests = [req for req in responses.calls if req.request.method == responses.POST]
    epic_issue_post = None
    for call in post_requests:
        if call.request.url.endswith("/repos/owner/repo/issues"):
            payload = json.loads(call.request.body)
            if payload.get("title") == "EPIC: Encounters & Overworld → Combat":
                epic_issue_post = payload
                break
    assert epic_issue_post is not None
    body = epic_issue_post.get("body", "")
    assert "- [ ] #101" in body
    assert "- [ ] #102" in body
    assert "- [ ] #103" in body
    assert "Linked Issues (Checklist)" in body


@responses.activate
def test_orchestrate_epic_updates_existing_epic(config_file: Path):
    repo = "owner/repo"
    token = "ghs_xxx"

    # Ensure epic label exists (already)
    responses.add(
        responses.GET,
        _api_url("/repos/owner/repo/labels/epic"),
        status=200,
        json={"name": "epic"},
    )

    # Ensure child labels exist
    for label in ["encounters", "overworld", "combat", "data", "boss"]:
        responses.add(
            responses.GET,
            _api_url(f"/repos/owner/repo/labels/{label}"),
            status=200,
            json={"name": label},
        )

    # Children found existing via search
    def search_child_matcher(request):
        q = request.params.get("q", "")
        if "Encounter Triggers (Overworld)" in q:
            return (200, {}, json.dumps({"items": [{"number": 111, "title": "Encounter Triggers (Overworld)"}]}))
        if "Enemy Formations by Tier" in q:
            return (200, {}, json.dumps({"items": [{"number": 112, "title": "Enemy Formations by Tier"}]}))
        if "Miniboss Gates (20/40/60/80)" in q:
            return (200, {}, json.dumps({"items": [{"number": 113, "title": "Miniboss Gates (20/40/60/80)"}]}))
        if "EPIC: Encounters & Overworld → Combat" in q:
            return (200, {}, json.dumps({"items": [{"number": 300, "title": "EPIC: Encounters & Overworld → Combat"}]}))
        return (200, {}, json.dumps({"items": []}))

    responses.add_callback(
        responses.GET,
        _api_url("/search/issues"),
        callback=search_child_matcher,
        content_type="application/json",
    )

    # Fetch full issue for each child and epic
    responses.add(responses.GET, _api_url("/repos/owner/repo/issues/111"), status=200, json={"number": 111, "title": "Encounter Triggers (Overworld)", "body": "", "labels": []})
    responses.add(responses.GET, _api_url("/repos/owner/repo/issues/112"), status=200, json={"number": 112, "title": "Enemy Formations by Tier", "body": "Existing body", "labels": []})
    responses.add(responses.GET, _api_url("/repos/owner/repo/issues/113"), status=200, json={"number": 113, "title": "Miniboss Gates (20/40/60/80)", "body": "", "labels": []})
    responses.add(responses.GET, _api_url("/repos/owner/repo/issues/300"), status=200, json={"number": 300, "title": "EPIC: Encounters & Overworld → Combat", "body": "Old body", "labels": [{"name": "epic"}]})

    # Update child bodies if empty
    responses.add(responses.PATCH, _api_url("/repos/owner/repo/issues/111"), status=200, json={"number": 111})
    responses.add(responses.PATCH, _api_url("/repos/owner/repo/issues/113"), status=200, json={"number": 113})

    # Add labels to children
    responses.add(responses.POST, _api_url("/repos/owner/repo/issues/111/labels"), status=200, json={"labels": []})
    responses.add(responses.POST, _api_url("/repos/owner/repo/issues/112/labels"), status=200, json={"labels": []})
    responses.add(responses.POST, _api_url("/repos/owner/repo/issues/113/labels"), status=200, json={"labels": []})

    # Update existing epic body/labels
    responses.add(responses.PATCH, _api_url("/repos/owner/repo/issues/300"), status=200, json={"number": 300})

    # Comments on children + epic
    for _ in range(4):
        responses.add(
            responses.POST,
            re.compile(r"https://api\.github\.com/repos/owner/repo/issues/\d+/comments"),
            status=201,
            json={"id": 123},
        )

    result = orchestrate_epic(repo=repo, token=token, config_path=str(config_file))

    assert result["epic_number"] == 300
    assert sorted([c["number"] for c in result["children"]]) == [111, 112, 113]

    # Ensure epic update call body contains checklist
    patch_calls = [c for c in responses.calls if c.request.method == responses.PATCH and c.request.url.endswith("/repos/owner/repo/issues/300")]
    assert patch_calls, "Expected PATCH to update epic"
    epic_patch_body = json.loads(patch_calls[0].request.body)
    assert "- [ ] #111" in epic_patch_body.get("body", "")
    assert "- [ ] #112" in epic_patch_body.get("body", "")
    assert "- [ ] #113" in epic_patch_body.get("body", "")
