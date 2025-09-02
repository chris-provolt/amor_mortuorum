#!/usr/bin/env python3
"""
Epic Issue Generator

Reads an epic YAML config and generates:
- Child issue markdown files (dry run) or creates issues via GitHub API
- A paste-ready checklist for the Epic issue
- Optionally updates the Epic doc with a synchronized checklist section (dry run only)

Usage (dry run):
  python tools/epics/generate_github_issues.py \
      --config configs/epics/bosses_balance.yaml \
      --epic-doc docs/epics/EPIC_Bosses_Balance.md \
      --dry-run \
      --output-dir .artifacts/issues

Usage (GitHub API live):
  export GH_TOKEN=ghp_...
  python tools/epics/generate_github_issues.py \
      --config configs/epics/bosses_balance.yaml \
      --repo owner/repo

Notes:
- In live mode, issues are created with labels and bodies. The Epic issue ID/URL is not auto-resolved; include the link manually in the Epic field in YAML if desired.
- This tool is idempotent only in dry-run mode. Live mode does not attempt to de-duplicate existing issues.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import pathlib
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Please install with `pip install pyyaml`."
    ) from exc

try:
    import requests  # type: ignore
except Exception:
    # We allow running without requests in dry-run mode.
    requests = None  # type: ignore


LOGGER = logging.getLogger("epicgen")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


@dataclasses.dataclass
class Epic:
    id: str
    title: str
    labels: List[str]
    target_window: str
    description: str
    acceptance: List[str]


@dataclasses.dataclass
class ChildIssue:
    id: str
    title: str
    labels: List[str]
    acceptance: List[str]
    body: str


@dataclasses.dataclass
class EpicConfig:
    epic: Epic
    children: List[ChildIssue]


class ConfigError(ValueError):
    pass


def sanitize_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\-_.]+", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


def load_config(path: str | pathlib.Path) -> EpicConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ConfigError("Top-level YAML must be a mapping")

    e = data.get("epic")
    c = data.get("children")
    if not isinstance(e, dict):
        raise ConfigError("Missing 'epic' mapping in YAML config")
    if not isinstance(c, list):
        raise ConfigError("Missing 'children' list in YAML config")

    # Validate epic
    for field in ("id", "title", "labels", "target_window", "description", "acceptance"):
        if field not in e:
            raise ConfigError(f"epic.{field} is required")
    if not isinstance(e["labels"], list):
        raise ConfigError("epic.labels must be a list")
    if not isinstance(e["acceptance"], list):
        raise ConfigError("epic.acceptance must be a list")

    epic = Epic(
        id=str(e["id"]),
        title=str(e["title"]),
        labels=[str(x) for x in e["labels"]],
        target_window=str(e["target_window"]),
        description=str(e["description"]),
        acceptance=[str(x) for x in e["acceptance"]],
    )

    # Validate children
    children: List[ChildIssue] = []
    seen_ids: set[str] = set()
    for idx, it in enumerate(c):
        if not isinstance(it, dict):
            raise ConfigError(f"children[{idx}] must be a mapping")
        for field in ("id", "title", "labels", "acceptance", "body"):
            if field not in it:
                raise ConfigError(f"children[{idx}].{field} is required")
        if not isinstance(it["labels"], list):
            raise ConfigError(f"children[{idx}].labels must be a list")
        if not isinstance(it["acceptance"], list):
            raise ConfigError(f"children[{idx}].acceptance must be a list")
        cid = str(it["id"]).strip()
        if cid in seen_ids:
            raise ConfigError(f"Duplicate child id: {cid}")
        seen_ids.add(cid)
        children.append(
            ChildIssue(
                id=cid,
                title=str(it["title"]),
                labels=[str(x) for x in it["labels"]],
                acceptance=[str(x) for x in it["acceptance"]],
                body=str(it["body"]).strip(),
            )
        )

    return EpicConfig(epic=epic, children=children)


def format_issue_body(epic: Epic, child: ChildIssue, epic_issue_url: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append(f"{child.body.strip()}\n")
    lines.append("Labels")
    lines.append(", ".join(child.labels))
    lines.append("")
    lines.append("Epic")
    if epic_issue_url:
        lines.append(epic_issue_url)
    else:
        lines.append(epic.title)
    lines.append("")
    lines.append("Acceptance")
    for a in child.acceptance:
        lines.append(f"- {a}")
    return "\n".join(lines).strip() + "\n"


def format_checklist(epic: Epic, children: List[ChildIssue], issue_links: Optional[Dict[str, str]] = None) -> str:
    lines: List[str] = []
    lines.append(f"# EPIC Checklist: {epic.title}\n")
    lines.append("Meta")
    lines.append(f"- Epic: {epic.title}")
    lines.append("- Source: configs/epics/bosses_balance.yaml\n")
    lines.append("Checklist")
    for child in children:
        title = child.title
        if issue_links and child.id in issue_links:
            title = f"[{title}]({issue_links[child.id]})"
        lines.append(f"- [ ] {title}")
    lines.append("\nInstructions")
    lines.append("- After creating child issues (via the generator tool or manually), paste this checklist as a comment on the Epic issue.")
    return "\n".join(lines) + "\n"


def write_issue_markdowns(out_dir: pathlib.Path, epic: Epic, children: List[ChildIssue], epic_issue_url: Optional[str]) -> List[pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files: List[pathlib.Path] = []
    for idx, child in enumerate(children, start=1):
        fname = f"{idx:02d}-{sanitize_filename(child.id or child.title)}.md"
        fpath = out_dir / fname
        body = format_issue_body(epic, child, epic_issue_url)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"# {child.title}\n\n")
            f.write(body)
        files.append(fpath)
        LOGGER.info("Wrote issue markdown: %s", fpath)
    return files


def write_checklist(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    LOGGER.info("Wrote checklist: %s", path)


def create_github_issues(repo: str, token: str, epic: Epic, children: List[ChildIssue]) -> Dict[str, Dict[str, Any]]:
    """
    Create issues on GitHub. Returns mapping child.id -> {number, url}.
    """
    if requests is None:  # pragma: no cover
        raise RuntimeError("requests is required for GitHub operations")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{repo}/issues"

    results: Dict[str, Dict[str, Any]] = {}
    for child in children:
        payload = {
            "title": child.title,
            "body": format_issue_body(epic, child),
            "labels": child.labels,
        }
        r = requests.post(api, headers=headers, json=payload, timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Failed to create issue '{child.title}': {r.status_code} {r.text}")
        data = r.json()
        results[child.id] = {"number": data.get("number"), "url": data.get("html_url")}
        LOGGER.info("Created issue #%s: %s", data.get("number"), data.get("html_url"))
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Bosses & Balance Epic issues and checklist")
    parser.add_argument("--config", required=True, help="Path to epic YAML config")
    parser.add_argument("--epic-doc", required=False, help="Path to Epic markdown doc")
    parser.add_argument("--output-dir", default=".artifacts/issues", help="Directory to write issue markdowns (dry-run)")
    parser.add_argument("--checklist-out", default="docs/epics/checklists/EPIC_Bosses_Balance_checklist.md", help="Checklist output path")
    parser.add_argument("--dry-run", action="store_true", help="Do not call GitHub API; write markdowns locally")
    parser.add_argument("--repo", help="GitHub repo in 'owner/name' form for live issue creation")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    epic_issue_url = None
    gh_token = os.environ.get("GH_TOKEN")
    if not args.dry_run and (not args.repo or not gh_token):
        LOGGER.warning("Missing --repo or GH_TOKEN; switching to dry-run mode")
        args.dry_run = True

    if args.dry_run:
        # Write issue markdown files
        out_dir = pathlib.Path(args.output_dir)
        write_issue_markdowns(out_dir, cfg.epic, cfg.children, epic_issue_url)
        # Write checklist
        checklist_md = format_checklist(cfg.epic, cfg.children)
        write_checklist(pathlib.Path(args.checklist_out), checklist_md)
        LOGGER.info("Dry-run complete")
        return 0

    # Live GitHub issue creation
    assert args.repo and gh_token
    created = create_github_issues(args.repo, gh_token, cfg.epic, cfg.children)

    # Build checklist with links
    links = {cid: meta["url"] for cid, meta in created.items() if meta.get("url")}
    checklist_md = format_checklist(cfg.epic, cfg.children, links)
    write_checklist(pathlib.Path(args.checklist_out), checklist_md)

    # Print summary JSON to stdout for optional scripting
    print(json.dumps({"created": created}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
