import argparse
import logging
import os
from typing import Dict, List, Tuple

import yaml

from .github_api import GitHubAPI


logger = logging.getLogger(__name__)


def build_epic_body(epic_cfg: Dict, child_issues: List[Dict]) -> str:
    """
    Build an epic issue body including summary, target window, and a checklist of child issues.
    Child issues should be a list of dicts with keys: number, title.
    """
    summary = epic_cfg.get("description", "")
    target = epic_cfg.get("target_window", "")
    acceptance = epic_cfg.get(
        "acceptance",
        [
            "Child issues exist and are linked in comments.",
            "Labels applied: `epic`.",
            "Progress can be tracked via linked issues checklist.",
        ],
    )
    lines: List[str] = []
    lines.append("## Summary")
    if summary:
        lines.append(summary.strip())
    if target:
        lines.append("")
        lines.append(f"Target Window: {target}")
    lines.append("")
    lines.append("## Acceptance")
    for a in acceptance:
        lines.append(f"- {a}")
    lines.append("")
    lines.append("## Linked Issues (Checklist)")
    for child in child_issues:
        lines.append(f"- [ ] #{child['number']} — {child['title']}")
    return "\n".join(lines).strip() + "\n"


def orchestrate_epic(repo: str, token: str, config_path: str, dry_run: bool = False) -> Dict:
    """
    Orchestrate creation/update of an Epic issue and its child issues per a YAML config.

    Returns a dict with epic_number and children mapping.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not cfg or "epic" not in cfg or "children" not in cfg:
        raise ValueError("Config must contain 'epic' and 'children' sections")

    epic_cfg = cfg["epic"]
    children_cfg = cfg["children"]
    epic_title: str = epic_cfg.get("title")
    if not epic_title:
        raise ValueError("Epic title is required in config")

    gh = GitHubAPI(repo=repo, token=token)

    # Ensure required labels exist
    epic_label_name = "epic"
    gh.ensure_label(epic_label_name, color="6f42c1", description="High-level work grouping (Epic)")

    # Ensure other labels used by children exist (best effort)
    for child in children_cfg:
        for label in child.get("labels", []) or []:
            gh.ensure_label(label, color=gh.sanitize_label_color(label))

    created_children: List[Dict] = []

    # Create/find each child issue
    for child in children_cfg:
        title = child.get("title")
        if not title:
            raise ValueError("Each child issue must have a title")
        body = child.get("description", "")
        labels = child.get("labels", [])

        existing = gh.search_issue_by_title(title)
        if existing:
            number = existing["number"]
            logger.info("Found existing child issue #%s: %s", number, title)
            # Optionally update body if provided and empty
            if body and not (existing.get("body") or "").strip():
                gh.update_issue(number, body=body)
            # Ensure labels applied if any new
            if labels:
                gh.add_labels(number, labels)
        else:
            logger.info("Creating child issue: %s", title)
            created = gh.create_issue(title=title, body=body, labels=labels)
            number = created["number"]
        created_children.append({"number": number, "title": title})

    # Create or update the epic
    existing_epic = gh.search_issue_by_title(epic_title)
    epic_body = build_epic_body(epic_cfg, created_children)

    if existing_epic:
        epic_number = existing_epic["number"]
        logger.info("Updating existing epic #%s: %s", epic_number, epic_title)
        # Merge labels and ensure 'epic'
        existing_labels = [l["name"] for l in existing_epic.get("labels", [])]
        labels = list(sorted(set(existing_labels + [epic_label_name] + epic_cfg.get("labels", []))))
        gh.update_issue(epic_number, body=epic_body, labels=labels)
    else:
        logger.info("Creating epic: %s", epic_title)
        labels = list(sorted(set([epic_label_name] + epic_cfg.get("labels", []))))
        created_epic = gh.create_issue(title=epic_title, body=epic_body, labels=labels)
        epic_number = created_epic["number"]

    # Link children back to epic via comments
    for child in created_children:
        child_num = child["number"]
        gh.comment_issue(child_num, f"Tracked by Epic #{epic_number} — {epic_title}")

    # Optional: comment on epic summarizing children
    children_list = "\n".join([f"- #{c['number']} — {c['title']}" for c in created_children])
    gh.comment_issue(epic_number, f"Linked child issues created/updated:\n\n{children_list}")

    return {"epic_number": epic_number, "children": created_children}


def main():
    parser = argparse.ArgumentParser(description="Create/Update GitHub Epic and child issues from YAML config.")
    parser.add_argument("--repo", required=True, help="Repository in 'owner/repo' format")
    parser.add_argument("--config", required=True, help="Path to epic YAML config")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token or set GITHUB_TOKEN env var")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("GitHub token is required via --token or GITHUB_TOKEN env var")

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    result = orchestrate_epic(repo=args.repo, token=args.token, config_path=args.config)
    logger.info("Epic #%s updated. %s child issues processed.", result["epic_number"], len(result["children"]))


if __name__ == "__main__":
    main()
