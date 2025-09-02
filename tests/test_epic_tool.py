import io
import os
import pathlib
import textwrap

import pytest

from tools.epics.generate_github_issues import (
    load_config,
    format_issue_body,
    format_checklist,
    write_issue_markdowns,
    write_checklist,
    ConfigError,
)


def test_load_config_valid_and_generate(tmp_path: pathlib.Path):
    cfg_path = pathlib.Path("configs/epics/bosses_balance.yaml")
    assert cfg_path.exists(), "expected default bosses_balance.yaml to exist"

    cfg = load_config(cfg_path)

    assert cfg.epic.title.startswith("EPIC: ")
    assert len(cfg.children) > 5
    # Ensure child fields are loaded
    first = cfg.children[0]
    assert first.title
    assert first.body
    assert isinstance(first.acceptance, list)

    # Generate issue body
    body = format_issue_body(cfg.epic, first)
    assert "Acceptance" in body
    for a in first.acceptance:
        assert a in body

    # Generate checklist
    checklist = format_checklist(cfg.epic, cfg.children)
    assert "EPIC Checklist" in checklist
    for child in cfg.children:
        assert child.title in checklist

    # Write markdowns
    out_dir = tmp_path / "issues"
    files = write_issue_markdowns(out_dir, cfg.epic, cfg.children, epic_issue_url=None)
    assert files, "expected files to be created"
    for f in files:
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert content.startswith("# ")
        assert "Labels" in content

    # Write checklist file
    chk_path = tmp_path / "checklist.md"
    write_checklist(chk_path, checklist)
    assert chk_path.exists()
    assert child.title.split(':')[0] in chk_path.read_text(encoding="utf-8")


def test_load_config_validation_errors(tmp_path: pathlib.Path):
    bad_yaml = textwrap.dedent(
        """
        epic:
          id: missing_fields_example
        children: []
        """
    )
    p = tmp_path / "bad.yaml"
    p.write_text(bad_yaml, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)

    dup_yaml = textwrap.dedent(
        """
        epic:
          id: ok
          title: T
          labels: [epic]
          target_window: any
          description: d
          acceptance: [a]
        children:
          - id: a
            title: A
            labels: [x]
            acceptance: [y]
            body: b
          - id: a
            title: B
            labels: [x]
            acceptance: [y]
            body: b
        """
    )
    p2 = tmp_path / "dup.yaml"
    p2.write_text(dup_yaml, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p2)
