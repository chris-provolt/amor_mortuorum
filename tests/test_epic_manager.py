import os

import pytest

from src.infra.github.epic import (
    IssueRef,
    build_checklist,
    embed_or_replace_block,
    load_epic_config,
)


def test_build_checklist_open_and_closed():
    children = [
        IssueRef(number=1, title="A", html_url="http://x/1", state="open"),
        IssueRef(number=2, title="B", html_url="http://x/2", state="closed"),
    ]
    ck = build_checklist(children)
    assert "Linked Issues" in ck
    # Open unchecked
    assert "- [ ] [A](http://x/1)" in ck
    # Closed checked
    assert "- [x] [B](http://x/2)" in ck


def test_embed_or_replace_block_appends_when_missing():
    body = "Intro text."
    content = "Line1\nLine2"
    out = embed_or_replace_block(body, content)
    assert "epic-manager:start" in out
    assert content in out


def test_embed_or_replace_block_replaces_when_present():
    original = "Before\n<!-- epic-manager:start -->\nOld\n<!-- epic-manager:end -->\nAfter"
    updated = embed_or_replace_block(original, "NewContent")
    assert "Old" not in updated
    assert "NewContent" in updated
    assert updated.count("epic-manager:start") == 1


def test_load_epic_config_schema(tmp_path):
    yml = tmp_path / "epic.yml"
    yml.write_text(
        """
        title: EPIC: Test
        body: Foo
        children:
          - title: Child1
            labels: [feature]
            body: details
        """,
        encoding="utf-8",
    )
    cfg = load_epic_config(str(yml))
    assert cfg.title == "EPIC: Test"
    assert cfg.children[0].title == "Child1"
    assert "epic" in cfg.labels
