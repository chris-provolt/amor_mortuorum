import pytest

from src.epic.epic_utils import (
    MARKER_START,
    MARKER_END,
    generate_checklist_section,
    upsert_section,
)


def test_generate_checklist_section_basic():
    children = [
        {"number": 101, "title": "First"},
        {"number": 102, "title": "Second"},
    ]
    section = generate_checklist_section(children)
    assert section.startswith("## Epic Progress\n\n" + MARKER_START)
    assert "- [ ] #101 First" in section
    assert "- [ ] #102 Second" in section
    assert section.strip().endswith(MARKER_END)


def test_generate_checklist_section_missing_number():
    with pytest.raises(ValueError):
        generate_checklist_section([{"title": "No number"}])


def test_upsert_section_appends_when_absent():
    body = "Initial body text."
    section = "## Epic Progress\n\n" + MARKER_START + "\n- [ ] #1 X\n\n" + MARKER_END
    result = upsert_section(body, section)
    assert body in result
    assert section in result


def test_upsert_section_replaces_existing():
    old_section = "## Epic Progress\n\n" + MARKER_START + "\n- [ ] #1 Old\n\n" + MARKER_END
    new_section = "## Epic Progress\n\n" + MARKER_START + "\n- [ ] #2 New\n\n" + MARKER_END
    body = f"Intro\n\n{old_section}\n\nOutro"

    updated = upsert_section(body, new_section)
    assert "#1 Old" not in updated
    assert "#2 New" in updated
    assert updated.startswith("Intro")
    assert updated.strip().endswith("Outro")


def test_upsert_section_handles_empty_body():
    section = "## Epic Progress\n\n" + MARKER_START + "\n- [ ] #3 Task\n\n" + MARKER_END
    updated = upsert_section("", section)
    assert updated.strip() == (section)
