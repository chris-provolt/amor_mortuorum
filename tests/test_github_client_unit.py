import json

import pytest
import json

import pytest
import responses

from src.am_epic.github_client import GitHubAPIError, GitHubClient


@responses.activate
def test_ensure_label_creates_when_missing():
    gh = GitHubClient(token="tok", repo="o/r")
    responses.add(responses.GET, "https://api.github.com/repos/o/r/labels/epic", status=404)
    responses.add(
        responses.POST,
        "https://api.github.com/repos/o/r/labels",
        json={"name": "epic", "color": "5319e7"},
        status=201,
    )
    lab = gh.ensure_label("epic", color="5319e7")
    assert lab["name"] == "epic"


@responses.activate
def test_search_issue_by_title_exact_match():
    gh = GitHubClient(token="tok", repo="o/r")
    # search returns two results but only one exact title
    responses.add(
        responses.GET,
        "https://api.github.com/search/issues?q=repo%3Ao%2Fr%20type%3Aissue%20in%3Atitle%20%22Hello%20World%22",
        json={
            "items": [
                {"number": 1, "title": "Hello world"},
                {"number": 2, "title": "Hello World"},
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/2",
        json={"number": 2, "title": "Hello World"},
        status=200,
    )
    issue = gh.search_issue_by_title("Hello World")
    assert issue["number"] == 2


@responses.activate
def test_error_response_raises():
    gh = GitHubClient(token="tok", repo="o/r")
    responses.add(
        responses.POST,
        "https://api.github.com/repos/o/r/issues",
        status=400,
        body=json.dumps({"message": "bad"}),
    )
    with pytest.raises(GitHubAPIError):
        gh.create_issue("t", "b")
