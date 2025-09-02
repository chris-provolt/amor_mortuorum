import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, validator

from .github_api import GitHubAPI

logger = logging.getLogger(__name__)

CHECKLIST_MARKER = "epic-checklist"
CHILD_LINKS_MARKER = "epic-child-links"
CHILD_EPIC_LINK_MARKER = "linked-to-epic"


class ChildIssueConfig(BaseModel):
    title: str
    body: str = ""
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)


class EpicConfig(BaseModel):
    title: str
    body: str = ""
    labels: List[str] = Field(default_factory=lambda: ["epic"])  # always include 'epic'
    children: List[ChildIssueConfig] = Field(default_factory=list)

    @validator("labels", pre=True, always=True)
    def ensure_epic_label(cls, v):
        labels = list(v or [])
        if "epic" not in labels:
            labels.append("epic")
        return labels


@dataclass
class EpicManager:
    api: GitHubAPI

    # ------------------- Public API -------------------
    def sync(self, config: EpicConfig) -> Dict[str, any]:
        """Synchronize Epic and its child issues according to the config.

        - Ensures labels exist
        - Creates or finds the Epic by title
        - Ensures child issues exist and link back to the Epic
        - Updates the Epic body with a progress checklist
        - Maintains a comment listing child issues for quick navigation
        """
        logger.info("Starting Epic sync: %s", config.title)

        # Ensure labels
        self._ensure_labels(config)

        # Find or create epic issue
        epic_issue = self.api.find_issue_by_title(config.title)
        if not epic_issue:
            logger.info("Epic not found, creating new issue for epic: %s", config.title)
            body = self._render_epic_body_with_checklist(config.body, [])
            epic_issue = self.api.create_issue(config.title, body, labels=config.labels)
        else:
            logger.info("Found existing Epic #%s", epic_issue.get("number"))
            # Ensure 'epic' label is present
            labels = [l["name"] if isinstance(l, dict) else l for l in epic_issue.get("labels", [])]
            if "epic" not in labels:
                labels.append("epic")
                labels = sorted(set(labels))
                self.api.update_issue(epic_issue["number"], labels=labels)

        epic_number = epic_issue["number"]

        # Ensure children exist
        child_issues: List[Dict[str, any]] = []
        for child_cfg in config.children:
            issue = self.api.find_issue_by_title(child_cfg.title)
            if not issue:
                logger.info("Creating child issue: %s", child_cfg.title)
                child_body = self._render_child_body(child_cfg, epic_number)
                issue = self.api.create_issue(child_cfg.title, child_body, labels=child_cfg.labels or None, assignees=child_cfg.assignees or None)
            else:
                logger.debug("Found existing child issue #%s: %s", issue.get("number"), child_cfg.title)
                # Add epic link comment on child (idempotent)
                self._upsert_child_epic_link_comment(issue["number"], epic_number)
            child_issues.append(issue)

        # Update epic checklist and child-links comment
        checklist = self._generate_checklist(child_issues)
        updated_body = self._render_epic_body_with_checklist(config.body, checklist)
        self.api.update_issue(epic_number, body=updated_body, labels=config.labels)

        # Summary comment for quick navigation
        self._upsert_epic_child_links_comment(epic_number, child_issues)

        return {
            "epic_number": epic_number,
            "child_numbers": [i["number"] for i in child_issues],
            "checklist": checklist,
        }

    # ------------------- Rendering -------------------
    def _render_epic_body_with_checklist(self, base_body: str, checklist_lines: List[str]) -> str:
        token_start = f"<!-- {CHECKLIST_MARKER}:start -->"
        token_end = f"<!-- {CHECKLIST_MARKER}:end -->"
        lines: List[str] = []
        if base_body.strip():
            lines.append(base_body.strip())
            lines.append("")
        lines.append("## Progress")
        lines.append(token_start)
        if checklist_lines:
            lines.extend(checklist_lines)
        else:
            lines.append("- [ ] No child issues linked yet.")
        lines.append(token_end)
        return "\n".join(lines).strip() + "\n"

    def _generate_checklist(self, child_issues: List[Dict[str, any]]) -> List[str]:
        checklist: List[str] = []
        for issue in child_issues:
            state = issue.get("state") or "open"
            checked = "x" if state == "closed" else " "
            number = issue.get("number")
            title = issue.get("title")
            checklist.append(f"- [{checked}] #{number} {title}")
        return checklist

    def _render_child_body(self, child_cfg: ChildIssueConfig, epic_number: int) -> str:
        base = child_cfg.body.strip()
        link = f"Linked to Epic #{epic_number}."
        meta = [
            "---",
            f"Parent Epic: #{epic_number}",
            "This issue was generated by the Epic manager.",
            "---",
        ]
        combined = "\n\n".join([base, "\n".join(meta), ""]).strip() + "\n"
        # Also add idempotent comment after creation
        # comment cannot be added here because we don't have issue number yet; handled in sync loop
        return combined

    # ------------------- Comments -------------------
    def _upsert_epic_child_links_comment(self, epic_number: int, child_issues: List[Dict[str, any]]) -> None:
        lines = ["### Linked Child Issues"]
        for issue in child_issues:
            num = issue.get("number")
            title = issue.get("title")
            state = issue.get("state")
            emoji = "✅" if state == "closed" else "⬜"
            lines.append(f"- {emoji} #{num} {title}")
        content = "\n".join(lines)
        self.api.upsert_marked_comment(epic_number, CHILD_LINKS_MARKER, content)

    def _upsert_child_epic_link_comment(self, child_number: int, epic_number: int) -> None:
        content = f"Linked to Epic #{epic_number}."
        self.api.upsert_marked_comment(child_number, CHILD_EPIC_LINK_MARKER, content)

    # ------------------- Labels -------------------
    def _ensure_labels(self, config: EpicConfig) -> None:
        # ensure epic label
        try:
            self.api.ensure_label("epic", color="6f42c1", description="Tracks a group of related issues")
        except Exception as e:
            logger.warning("Failed to ensure label 'epic': %s", e)
        # ensure any other labels from epic and children
        label_set = set(config.labels)
        for child in config.children:
            label_set.update(child.labels)
        for label in sorted(label_set):
            if label == "epic":
                continue
            try:
                self.api.ensure_label(label, color="0e8a16")
            except Exception as e:
                logger.warning("Failed to ensure label '%s': %s", label, e)


# ------------------- Config Loader -------------------

def load_epic_config(path: str | os.PathLike[str]) -> EpicConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Epic config not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Support top-level 'epic' key or direct fields
    if "epic" in data and isinstance(data["epic"], dict):
        data = data["epic"]
    return EpicConfig(**data)


def discover_epic_config_by_title(config_dir: str | os.PathLike[str], title: str) -> Optional[str]:
    """Search configs directory to find a config whose title matches."""
    p = Path(config_dir)
    for yml in list(p.glob("*.yml")) + list(p.glob("*.yaml")):
        try:
            cfg = load_epic_config(yml)
        except Exception:
            continue
        if cfg.title.strip() == title.strip():
            return str(yml)
    return None
