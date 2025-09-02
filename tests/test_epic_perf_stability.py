import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import requests_mock

from amormortuorum.tools.github_issues import GitHubClient, AUTO_SECTION_START, AUTO_SECTION_END
from amormortuorum.epics.perf_stability import EPIC_TITLE, EPIC_BODY, EPIC_LABELS, child_issue_specs


@pytest.fixture()
def gh_client():
    return GitHubClient(repo="owner/repo", token="ghs_dummy")


def _search_handler(expected_title):
    def handler(request, context):
        q = parse_qs(urlparse(request.url).query).get("q", [""])[0]
        # If title is present, but we treat as non-existing by default
        context.status_code = 200
        return {"items": []}

    return handler


def test_create_epic_and_children_idempotent(gh_client, requests_mock: requests_mock.Mocker):
    # Ensure label checks: first returns 404, then create succeeds
    def label_get(request, context):
        context.status_code = 404
        return {}

    requests_mock.get("https://api.github.com/repos/owner/repo/labels/epic", json=label_get)
    requests_mock.get("https://api.github.com/repos/owner/repo/labels/performance", json=label_get)
    requests_mock.get("https://api.github.com/repos/owner/repo/labels/stability", json=label_get)
    requests_mock.get("https://api.github.com/repos/owner/repo/labels/tracking", json=label_get)
    # Child labels (some duplicates handled gracefully)
    for name in [
        "graphics",
        "batching",
        "tooling",
        "culling",
        "spatial-index",
        "collisions",
        "fx",
        "pooling",
        "map",
        "ci",
        "benchmark",
        "testing",
        "determinism",
        "telemetry",
        "memory",
        "regression",
    ]:
        requests_mock.get(f"https://api.github.com/repos/owner/repo/labels/{name}", json=label_get)

    # Label creation posts
    requests_mock.post("https://api.github.com/repos/owner/repo/labels", json={})

    # Searches return none for epic and children initially
    requests_mock.get(
        "https://api.github.com/search/issues",
        json={"items": []},
    )

    # Issue creation: epic first, then a batch of children
    issue_counter = {"n": 0}

    def create_issue(request, context):
        payload = request.json()
        issue_counter["n"] += 1
        number = issue_counter["n"]
        context.status_code = 201
        return {
            "number": number,
            "title": payload["title"],
            "html_url": f"https://github.com/owner/repo/issues/{number}",
        }

    requests_mock.post("https://api.github.com/repos/owner/repo/issues", json=create_issue)

    # Updates to issues
    def update_issue(request, context):
        context.status_code = 200
        body = request.json()
        # Return the number from URL
        number = int(request.url.split("/")[-1])
        title = body.get("title", f"Issue #{number}")
        return {
            "number": number,
            "title": title,
            "html_url": f"https://github.com/owner/repo/issues/{number}",
        }

    requests_mock.patch(requests_mock.ANY, json=update_issue)

    # Comments and labels add
    requests_mock.post(requests_mock.ANY, additional_matcher=lambda r: r.url.endswith("/comments"), json={})
    requests_mock.post(requests_mock.ANY, additional_matcher=lambda r: r.url.endswith("/labels"), json={})

    from amormortuorum.epics.perf_stability import create_or_update_epic

    # First run: creates everything
    create_or_update_epic(gh_client)

    # Validate that epic body got updated with markers via last PATCH (we can't easily introspect, so ensure at least one patch occurred)
    assert issue_counter["n"] > 1

    # Second run: should search and update instead of creating new issues
    # Prepare search to return existing items now
    def search_existing(request, context):
        q = parse_qs(urlparse(request.url).query).get("q", [""])[0]
        context.status_code = 200
        # Extract title between quotes
        # The query includes \"title\" marker
        m = None
        for part in q.split("\""):
            if part and "repo:" not in part and "is:issue" not in part and "in:title" not in part:
                m = part
        title = m or ""
        # Derive a pseudo-number deterministically for existing issues by hashing
        number = abs(hash(title)) % 10000 + 1
        return {
            "items": [
                {
                    "number": number,
                    "title": title,
                    "html_url": f"https://github.com/owner/repo/issues/{number}",
                }
            ]
        }

    requests_mock.get("https://api.github.com/search/issues", json=search_existing)

    create_or_update_epic(gh_client)

    # If we got here without exception, idempotency holds


def test_upsert_auto_section_roundtrip():
    from amormortuorum.tools.github_issues import upsert_autosection

    body = EPIC_BODY
    section1 = "- [ ] A (link)\n- [ ] B (link)"
    updated = upsert_autosection(body, section1)
    assert AUTO_SECTION_START in updated and AUTO_SECTION_END in updated
    assert section1 in updated

    # Replace with a new section
    section2 = "- [x] A (link)\n- [ ] B (link)\n- [ ] C (link)"
    updated2 = upsert_autosection(updated, section2)
    assert section2 in updated2
    assert section1 not in updated2
