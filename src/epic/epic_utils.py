from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

MARKER_START = "<!-- epic:auto:children -->"
MARKER_END = "<!-- /epic:auto:children -->"


def generate_checklist_section(children: List[dict]) -> str:
    """
    Generate a GitHub Markdown section containing a checklist of child issues.

    The section is wrapped with marker comments so it can be idempotently updated.

    Args:
        children: A list of dictionaries with keys 'number' (int) and 'title' (str).

    Returns:
        A markdown string with the progress header, markers, and list items like:
        - [ ] #123 Title
    """
    lines = ["## Epic Progress", "", MARKER_START, ""]
    for ch in children:
        num = ch.get("number")
        title = ch.get("title", "")
        if num is None:
            raise ValueError("Each child dict must include an issue 'number'.")
        lines.append(f"- [ ] #{num} {title}".rstrip())
    lines += ["", MARKER_END]
    return "\n".join(lines)


def upsert_section(body: Optional[str], section: str) -> str:
    """
    Insert or replace the epic progress section in an issue body.

    If markers are present, content between them is replaced. Otherwise, the
    section is appended to the end with a separating blank line.

    Args:
        body: The current issue body (may be None or empty).
        section: The new section to insert or replace, including markers.

    Returns:
        The updated body string.
    """
    body = (body or "").rstrip("\n")
    start_idx = body.find(MARKER_START)
    end_idx = body.find(MARKER_END)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        # Replace existing marked section
        before = body[:start_idx].rstrip()
        after = body[end_idx + len(MARKER_END):].lstrip("\n")
        if before:
            updated = before + "\n\n" + section
        else:
            updated = section
        if after:
            updated = updated.rstrip("\n") + "\n\n" + after
        else:
            updated = updated.rstrip("\n") + "\n"
        return updated

    # Append if no markers present
    if body:
        return body + "\n\n" + section + "\n"
    return section + "\n"


@dataclass
class ChildIssue:
    number: int
    title: str


def _cli_generate_section(children_json_path: str) -> None:
    with open(children_json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Normalize into list of dicts
    items: List[dict] = []
    for it in raw:
        if isinstance(it, dict):
            items.append({"number": it.get("number"), "title": it.get("title", "")})
        else:
            raise ValueError("Children JSON must contain objects with number and title")
    print(generate_checklist_section(items))


def main(argv: Optional[List[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Epic utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate-section", help="Generate checklist section from JSON list")
    g.add_argument("children_json", help="Path to JSON array of {number, title}")

    u = sub.add_parser("upsert", help="Upsert section into body")
    u.add_argument("body_path", help="Path to file containing body")
    u.add_argument("section_path", help="Path to file containing section")

    args = parser.parse_args(argv)

    if args.cmd == "generate-section":
        _cli_generate_section(args.children_json)
    elif args.cmd == "upsert":
        with open(args.body_path, "r", encoding="utf-8") as f:
            body = f.read()
        with open(args.section_path, "r", encoding="utf-8") as f:
            section = f.read()
        print(upsert_section(body, section))


if __name__ == "__main__":
    main()
