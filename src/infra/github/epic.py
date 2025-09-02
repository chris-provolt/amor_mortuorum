from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .client import GitHubClient

logger = logging.getLogger(__name__)

EPIC_BLOCK_START = "<!-- epic-manager:start -->"
EPIC_BLOCK_END = "<!-- epic-manager:end -->"


class IssueConfig(BaseModel):
    title: str = Field(..., description="Issue title")
    body: str = Field("", description="Issue body")
    labels: List[str] = Field(default_factory=list, description="Labels to apply")


class EpicConfig(BaseModel):
    title: str = Field(..., description="Epic issue title")
    body: str = Field("", description="Epic description/body")
    labels: List[str] = Field(default_factory=lambda: ["epic"], description="Labels for the epic issue")
    children: List[IssueConfig] = Field(default_factory=list, description="Child issues")

    @field_validator("labels")
    @classmethod
    def ensure_epic_label(cls, v: List[str]) -> List[str]:
        if "epic" not in v:
            v.append("epic")
        return v


@dataclass
class IssueRef:
    number: int
    title: str
    html_url: str
    state: str


def load_epic_config(path: str) -> EpicConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        return EpicConfig.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid epic config: {e}") from e


def build_checklist(child_issues: List[IssueRef]) -> str:
    lines = ["Linked Issues"]
    lines.append("")
    for it in child_issues:
        checked = "x" if it.state == "closed" else " "
        lines.append(f"- [{checked}] [{it.title}]({it.html_url})")
    return "\n".join(lines)


def embed_or_replace_block(original_body: str, block_content: str) -> str:
    """Embeds or replaces the managed block inside the epic body.

    If markers exist, replace the content between them. Otherwise, append the block.
    """
    block = f"{EPIC_BLOCK_START}\n{block_content}\n{EPIC_BLOCK_END}"
    if EPIC_BLOCK_START in original_body and EPIC_BLOCK_END in original_body:
        pattern = re.compile(re.escape(EPIC_BLOCK_START) + r"[\s\S]*?" + re.escape(EPIC_BLOCK_END), re.MULTILINE)
        new_body = pattern.sub(block, original_body)
        return new_body
    # Append with spacing
    if original_body and not original_body.endswith("\n"):
        original_body += "\n\n"
    elif original_body and original_body.endswith("\n"):
        original_body += "\n"
    return original_body + block


def upsert_issue(client: GitHubClient, cfg: IssueConfig) -> Dict[str, Any]:
    existing = client.search_issue_by_title(cfg.title)
    if existing:
        # Only update body if different
        current_body = existing.get("body") or ""
        if cfg.body and cfg.body.strip() != (current_body or "").strip():
            logger.info("Updating existing issue #%s: %s", existing.get("number"), cfg.title)
            existing = client.update_issue(existing["number"], body=cfg.body)
        # Apply missing labels if any
        if cfg.labels:
            current_labels = {lbl["name"] for lbl in existing.get("labels", [])}
            missing = [l for l in cfg.labels if l not in current_labels]
            if missing:
                client.add_labels(existing["number"], missing)
        return existing
    logger.info("Creating new issue: %s", cfg.title)
    created = client.create_issue(cfg.title, cfg.body, labels=cfg.labels or None)
    return created


def upsert_epic_with_children(client: GitHubClient, epic_cfg: EpicConfig, dry_run: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    # Ensure epic label exists in repo
    if not dry_run:
        client.ensure_label("epic", color="6f42c1", description="Parent tracking issue for an epic")
    else:
        logger.info("[DRY-RUN] Would ensure label 'epic'")

    created_children: List[Dict[str, Any]] = []
    for child in epic_cfg.children:
        if not dry_run:
            # Upsert child issue
            issue = upsert_issue(client, child)
            created_children.append(issue)
        else:
            logger.info("[DRY-RUN] Would upsert child issue: %s", child.title)
            # fabricate a pseudo issue for output
            created_children.append({
                "number": 0,
                "title": child.title,
                "html_url": f"https://github.com/{client.repo}/issues/0",
                "state": "open",
                "labels": [{"name": l} for l in (child.labels or [])],
                "body": child.body,
            })

    # Build checklist
    child_refs = [
        IssueRef(
            number=it["number"],
            title=it["title"],
            html_url=it["html_url"],
            state=it.get("state", "open"),
        )
        for it in created_children
    ]
    checklist = build_checklist(child_refs)

    # Upsert epic issue
    if not dry_run:
        existing_epic = client.search_issue_by_title(epic_cfg.title)
    else:
        existing_epic = None

    if existing_epic:
        new_body = embed_or_replace_block(existing_epic.get("body") or "", checklist)
        logger.info("Updating epic issue #%s body block", existing_epic["number"])
        epic_issue = client.update_issue(existing_epic["number"], body=new_body)
        # Ensure label present
        current_labels = {lbl["name"] for lbl in epic_issue.get("labels", [])}
        if "epic" not in current_labels:
            client.add_labels(epic_issue["number"], [l for l in epic_cfg.labels])
    else:
        body = embed_or_replace_block(epic_cfg.body or "", checklist)
        logger.info("Creating epic issue: %s", epic_cfg.title)
        if not dry_run:
            epic_issue = client.create_issue(epic_cfg.title, body, labels=epic_cfg.labels)
        else:
            epic_issue = {
                "number": 0,
                "title": epic_cfg.title,
                "body": body,
                "html_url": f"https://github.com/{client.repo}/issues/0",
                "labels": [{"name": l} for l in epic_cfg.labels],
            }

    # Link back in comments
    if not dry_run and epic_issue.get("number"):
        epic_number = epic_issue["number"]
        for child in created_children:
            try:
                client.create_comment(child["number"], f"Parent epic: #{epic_number}")
            except Exception as e:
                logger.warning("Failed to comment on child #%s: %s", child.get("number"), e)

    return epic_issue, created_children


def format_summary_comment(epic_issue: Dict[str, Any], children: List[Dict[str, Any]]) -> str:
    lines = [
        f"Epic: {epic_issue.get('title')} (#{epic_issue.get('number')})",
        "",
        "Children:",
    ]
    for it in children:
        lines.append(f"- {it['title']} (#{it['number']}) - {it.get('html_url')}")
    return "\n".join(lines)
