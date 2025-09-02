import json
import os

import responses

from amormortuorum.issue_tools.epic_generator import EpicGenerator
from amormortuorum.issue_tools.github_client import GitHubClient


@responses.activate
def test_creates_labels_and_issues(tmp_path):
    # Arrange mock endpoints
    repo = "owner/repo"
    token = "tkn"
    client = GitHubClient(repo=repo, token=token)
    gen = EpicGenerator(client)
    cfg_path = os.path.join("configs", "epics", "turn_based_combat.yaml")
    cfg = gen.load_config(cfg_path)

    # list labels empty
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{repo}/labels",
        json=[],
        status=200,
    )
    # create label(s)
    responses.add(responses.POST, f"https://api.github.com/repos/{repo}/labels", json={"name": "epic"}, status=201)
    # search no epic, no children
    responses.add(responses.GET, "https://api.github.com/search/issues", json={"items": []}, status=200)

    # create child issues: we will only mock the first two to keep it bounded
    # For simplicity, respond 201 to any create issue call with incrementing numbers
    create_issue_calls = []

    def create_issue_callback(request):
        payload = json.loads(request.body)
        create_issue_calls.append(payload["title"]) 
        num = len(create_issue_calls)
        return (201, {}, json.dumps({"number": num, "title": payload["title"]}))

    responses.add_callback(
        responses.POST,
        f"https://api.github.com/repos/{repo}/issues",
        callback=create_issue_callback,
        content_type="application/json",
    )

    # update epic not existing -> create
    # After children, first search result for epic returns empty, then create epic
    responses.add(
        responses.POST,
        f"https://api.github.com/repos/{repo}/issues",
        json={"number": 999, "title": cfg.epic.title},
        status=201,
    )

    # comments on children and epic
    responses.add(responses.POST, f"https://api.github.com/repos/{repo}/issues/1/comments", json={"id": 1}, status=201)
    responses.add(responses.POST, f"https://api.github.com/repos/{repo}/issues/2/comments", json={"id": 2}, status=201)
    responses.add(responses.POST, f"https://api.github.com/repos/{repo}/issues/999/comments", json={"id": 3}, status=201)

    # Act
    result = gen.generate(cfg, dry_run=False)

    # Assert
    assert result["epic_number"] == 999
    assert isinstance(result["children"], dict)
    assert len(result["children"]) == len(cfg.children)
