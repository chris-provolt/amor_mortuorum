import logging
from typing import Dict, List

from .github_client import GitHubClient
from .models import EpicSpec

logger = logging.getLogger(__name__)

CHECKLIST_START = "<!-- epic-checklist:start -->"
CHECKLIST_END = "<!-- epic-checklist:end -->"
EPIC_COMMENT_MARKER = "<!-- generated-by:am-epic -->"


class EpicManager:
    """Orchestrates creation and linking of an Epic with its child issues."""

    def __init__(self, gh: GitHubClient) -> None:
        self.gh = gh

    def apply(self, spec: EpicSpec) -> Dict[str, int]:
        """
        Ensure EPIC issue and all child issues exist, are linked, and the epic contains
        a progress checklist. Returns a dict with epic and child issue numbers.
        """
        # Ensure label 'epic' exists
        if "epic" not in [label.lower() for label in spec.labels]:
            spec.labels = [*spec.labels, "epic"]
        self.gh.ensure_label("epic", color="5319e7", description="Epic grouping issue")
        self.gh.ensure_label("epic-child", color="c2e0c6", description="Child of an Epic")

        epic = self._upsert_issue(spec.title, spec.body, spec.labels, spec.assignees)
        epic_number = epic["number"]
        logger.info("Epic #%s ready", epic_number)

        child_numbers: List[int] = []
        for child in spec.children:
            # Ensure child exists
            child_labels = list({*child.labels, "epic-child"})
            child_issue = self._upsert_issue(
                child.title,
                child.body,
                child_labels,
                child.assignees,
            )
            child_number = child_issue["number"]
            child_numbers.append(child_number)

            # Comment on child linking back to epic (idempotent-update)
            self._ensure_child_comment(child_number, epic_number)

        # Update epic body with dynamic checklist
        updated_body = self._build_epic_body_with_checklist(
            epic.get("body") or spec.body,
            child_numbers,
        )
        if updated_body != epic.get("body"):
            epic = self.gh.update_issue(epic_number, body=updated_body)

        # Add or update an epic comment listing the children
        self._ensure_epic_comment(epic_number, child_numbers)

        return {"epic": epic_number, "children": len(child_numbers)}

    def _upsert_issue(
        self, title: str, body: str, labels: List[str], assignees: List[str]
    ) -> Dict:
        existing = self.gh.search_issue_by_title(title)
        if existing:
            logger.debug("Issue exists: '%s' (#%s)", title, existing.get("number"))
            # Ensure required labels are present
            existing_labels = [
                label.get("name") if isinstance(label, dict) else label
                for label in existing.get("labels", [])
            ]
            missing = [label for label in labels if label not in existing_labels]
            if missing:
                self.gh.add_labels(existing["number"], missing)
            # Optionally refresh body if missing checklist markers for epic only; but keep user's edits for children
            return existing
        return self.gh.create_issue(title=title, body=body, labels=labels, assignees=assignees)

    def _build_epic_body_with_checklist(self, base_body: str, child_numbers: List[int]) -> str:
        # Compose checklist section
        lines = ["## Progress", "", "- [ ] Link and track child issues:"]
        for n in child_numbers:
            issue = self.gh.get_issue(n)
            checked = issue.get("state") == "closed"
            title = issue.get("title", "")
            checkbox = "x" if checked else " "
            lines.append(f"  - [{checkbox}] #{n} {title}")
        checklist = "\n".join(lines)

        if CHECKLIST_START in base_body and CHECKLIST_END in base_body:
            start_idx = base_body.index(CHECKLIST_START) + len(CHECKLIST_START)
            end_idx = base_body.index(CHECKLIST_END)
            new_body = base_body[:start_idx] + "\n" + checklist + "\n" + base_body[end_idx:]
        else:
            # Append scaffolded section
            sep = "\n\n" if not base_body.endswith("\n") else "\n"
            new_body = f"{base_body}{sep}{CHECKLIST_START}\n{checklist}\n{CHECKLIST_END}"
        return new_body

    def _ensure_epic_comment(self, epic_number: int, child_numbers: List[int]) -> None:
        comment_body = [
            EPIC_COMMENT_MARKER,
            "Child issues for this Epic:",
            "",
        ]
        for n in child_numbers:
            issue = self.gh.get_issue(n)
            issue_title = issue.get("title", "")
            comment_body.append(f"- #{n} {issue_title}")
        body = "\n".join(comment_body)

        comments = self.gh.list_comments(epic_number)
        gen_comment = next((c for c in comments if EPIC_COMMENT_MARKER in c.get("body", "")), None)
        if gen_comment:
            logger.debug("Updating epic generated comment")
            self.gh.update_comment(gen_comment["id"], body)
        else:
            logger.debug("Creating epic generated comment")
            self.gh.create_comment(epic_number, body)

    def _ensure_child_comment(self, child_number: int, epic_number: int) -> None:
        comments = self.gh.list_comments(child_number)
        marker = f"{EPIC_COMMENT_MARKER} epic:{epic_number}"
        desired = f"{marker}\nThis issue is part of Epic #{epic_number}."
        gen_comment = next((c for c in comments if marker in c.get("body", "")), None)
        if gen_comment:
            # Nothing to change currently
            return
        self.gh.create_comment(child_number, desired)
