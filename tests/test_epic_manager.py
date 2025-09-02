import json
import os
from urllib.parse import urlparse, parse_qs

import pytest
import responses

from src.epics.epic_manager import apply_epic_from_file


@pytest.fixture(autouse=True)
def set_env_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test_token")


def _json(body):
    return json.loads(body.decode("utf-8"))


@responses.activate
def test_apply_relics_epic_creates_epic_and_children(tmp_path):
    owner = "testorg"
    repo = "amormortuorum"
    full_repo = f"{owner}/{repo}"

    # Prepare config file copy in temp path (use repository config content)
    config_src = os.path.join(os.path.dirname(__file__), "..", "configs", "epics", "relics_of_the_veil.yaml")
    config_src = os.path.abspath(config_src)
    cfg = tmp_path / "relics_of_the_veil.yaml"
    cfg.write_text(open(config_src, "r", encoding="utf-8").read(), encoding="utf-8")

    base = "https://api.github.com"

    # 1) Ensure labels: accept any POST to labels
    def labels_callback(request):
        payload = _json(request.body)
        name = payload.get("name")
        return (201, {}, json.dumps({"name": name, "color": payload.get("color", "B60205")}))

    responses.add_callback(
        responses.POST,
        f"{base}/repos/{owner}/{repo}/labels",
        callback=lambda req: labels_callback(req),
        content_type="application/json",
    )

    # 2) Search issues: return no results for any query
    def search_callback(request):
        parsed = urlparse(request.url)
        q = parse_qs(parsed.query).get("q", [""])[0]
        return (200, {}, json.dumps({"total_count": 0, "items": []}))

    responses.add_callback(
        responses.GET,
        f"{base}/search/issues",
        callback=lambda req: search_callback(req),
        content_type="application/json",
    )

    # 3) Create issues: assign incrementing numbers
    issue_counter = {"n": 120}

    def issues_create_callback(request):
        issue_counter["n"] += 1
        payload = _json(request.body)
        number = issue_counter["n"]
        return (
            201,
            {},
            json.dumps(
                {
                    "number": number,
                    "title": payload["title"],
                    "body": payload.get("body", ""),
                    "state": "open",
                }
            ),
        )

    responses.add_callback(
        responses.POST,
        f"{base}/repos/{owner}/{repo}/issues",
        callback=lambda req: issues_create_callback(req),
        content_type="application/json",
    )

    # 4) Add labels to issue
    def issues_labels_callback(request):
        payload = _json(request.body)
        return (200, {}, json.dumps([{"name": lbl} for lbl in payload.get("labels", [])]))

    responses.add_callback(
        responses.POST,
        responses.re.compile(rf"{base}/repos/{owner}/{repo}/issues/\d+/labels"),
        callback=lambda req: issues_labels_callback(req),
        content_type="application/json",
    )

    # 5) Comment on issues
    def issues_comment_callback(request):
        payload = _json(request.body)
        return (201, {}, json.dumps({"id": 999, "body": payload.get("body", "")}))

    responses.add_callback(
        responses.POST,
        responses.re.compile(rf"{base}/repos/{owner}/{repo}/issues/\d+/comments"),
        callback=lambda req: issues_comment_callback(req),
        content_type="application/json",
    )

    # 6) Patch epic body update
    updated_bodies = []

    def issues_patch_callback(request):
        payload = _json(request.body)
        updated_bodies.append(payload.get("body", ""))
        return (200, {}, json.dumps({"number": 121, "body": payload.get("body", "")}))

    responses.add_callback(
        responses.PATCH,
        responses.re.compile(rf"{base}/repos/{owner}/{repo}/issues/\d+"),
        callback=lambda req: issues_patch_callback(req),
        content_type="application/json",
    )

    result = apply_epic_from_file(repo=full_repo, config_path=str(cfg), token=os.getenv("GITHUB_TOKEN"), dry_run=False)

    # Expect: 1 epic + N children from config (6 children defined)
    assert result["epic"] >= 121
    assert result["children"] == 6

    # Verify the epic body contains checklist with child links
    assert updated_bodies, "Epic body should have been updated"
    body = updated_bodies[-1]
    assert "## Linked Issues" in body
    assert "Labels applied: epic" in body
    # All child titles should appear
    for title in [
        "Relics: Data schema and registry",
        "Relics: Acquisition logic and persistence",
        "Relics: Final relic unlock and conditions",
        "Relics: Passive toggles UI and save-state",
        "Relics: Content data for 9+1 relics",
        "Relics: Tests, validation, and docs",
    ]:
        assert title in body
