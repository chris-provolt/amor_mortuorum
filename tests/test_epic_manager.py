import tempfile
from typing import Any, Dict, List
from tools.epics.epic_manager import (
    load_config,
    process_epic,
    MARKER_START,
    MARKER_END,
)


class FakeLabel:
    def __init__(self, name: str):
        self.name = name


class FakeComment:
    def __init__(self, body: str):
        self.body = body
    def edit(self, body: str):
        self.body = body


class FakeIssue:
    _num = 0
    def __init__(self, title: str, body: str, labels: List[FakeLabel]):
        FakeIssue._num += 1
        self.title = title
        self.body = body
        self.labels = labels
        self.number = FakeIssue._num
        self._comments: List[FakeComment] = []
    def get_comments(self):
        return list(self._comments)
    def create_comment(self, body: str):
        c = FakeComment(body)
        self._comments.append(c)
        return c
    def edit(self, body: str = None):
        if body is not None:
            self.body = body


class FakeRepo:
    def __init__(self, full_name: str = "owner/repo"):
        self.full_name = full_name
        self._labels: Dict[str, FakeLabel] = {}
        self._issues: List[FakeIssue] = []
    def get_labels(self):
        return list(self._labels.values())
    def create_label(self, name: str, color: str, description: str):
        lbl = FakeLabel(name)
        self._labels[name.lower()] = lbl
        return lbl
    def get_issues(self, state: str = "open"):
        return list(self._issues)
    def create_issue(self, title: str, body: str, labels: List[FakeLabel]):
        issue = FakeIssue(title, body, labels)
        self._issues.append(issue)
        return issue


def minimal_config_yaml() -> str:
    return """
    title: EPIC: Fog of War & Minimap
    body: |
      Test epic body
    labels: [epic]
    children:
      - key: child-1
        title: FOV: Visibility + Explored Tiles Grid
        labels: [feature, map, fov]
        body: test child body 1
      - key: child-2
        title: Minimap: Rendering Overlay
        labels: [feature, ui, map]
        body: test child body 2
    """


def test_load_config_and_process_epic_creates_issues(tmp_path):
    # Write temp config
    cfg_path = tmp_path / "epic.yml"
    cfg_path.write_text(minimal_config_yaml())

    cfg = load_config(str(cfg_path))
    repo = FakeRepo()

    summary = process_epic(repo, cfg, dry_run=False)

    # Should have created 1 epic + 2 children
    assert len(repo._issues) == 3

    # Epic should have checklist comment with both markers
    epic_issue = next(i for i in repo._issues if i.title == "EPIC: Fog of War & Minimap")
    comments = epic_issue.get_comments()
    assert any(MARKER_START in c.body and MARKER_END in c.body for c in comments)

    # Each child should have backlink comment
    for title in ("FOV: Visibility + Explored Tiles Grid", "Minimap: Rendering Overlay"):
        child = next(i for i in repo._issues if i.title == title)
        assert any("Linked to Epic: #" in c.body for c in child.get_comments())


def test_idempotent_rerun_updates_comment_not_duplicate(tmp_path):
    cfg_path = tmp_path / "epic.yml"
    cfg_path.write_text(minimal_config_yaml())

    cfg = load_config(str(cfg_path))
    repo = FakeRepo()

    summary1 = process_epic(repo, cfg, dry_run=False)
    # Capture comment count on epic
    epic_issue = next(i for i in repo._issues if i.title == "EPIC: Fog of War & Minimap")
    initial_comment_count = len(epic_issue.get_comments())

    # Re-run
    summary2 = process_epic(repo, cfg, dry_run=False)

    # No new issues should be created, still 3 total
    assert len(repo._issues) == 3

    # Checklist comment should be updated in place (no new managed comment)
    managed_comments = [c for c in epic_issue.get_comments() if MARKER_START in c.body and MARKER_END in c.body]
    assert len(managed_comments) == 1
    assert len(epic_issue.get_comments()) == initial_comment_count


def test_dry_run_mode_like_objects(tmp_path):
    # In dry-run, numbers may be -1; ensure no crash building checklist
    cfg_path = tmp_path / "epic.yml"
    cfg_path.write_text(minimal_config_yaml())

    cfg = load_config(str(cfg_path))

    # Simulate dry-run by using an isolated repo but passing dry_run=True
    repo = FakeRepo()
    # We don't create labels/issues via repo in dry-run path of create_issue() here,
    # but process_epic should still work and attach a checklist comment to the epic.
    summary = process_epic(repo, cfg, dry_run=True)
    # Summary may not have real numbers in dry-run; but function should complete.
    assert "epic_number" in summary
