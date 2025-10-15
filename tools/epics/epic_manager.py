import argparse
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required. Add 'PyYAML' to your dependencies.") from exc

# Optional import: only needed when running against GitHub. Unit tests mock the repo API.
try:  # pragma: no cover - covered via integration usage, not unit tests
    from github import Github  # type: ignore
    from github.GithubException import GithubException  # type: ignore
except Exception:  # pragma: no cover
    Github = None  # type: ignore
    GithubException = Exception  # type: ignore


MARKER_START = "<!-- EPIC-CHILDREN START -->"
MARKER_END = "<!-- EPIC-CHILDREN END -->"


class EpicManagerError(Exception):
    """Domain exception for Epic Manager errors."""


def load_config(path: str) -> Dict[str, Any]:
    """Load epic configuration YAML.

    Expected schema:
    title: str
    body: str
    labels: [str]
    children: [
      { key: str, title: str, body: str, labels: [str] }
    ]
    """
    if not os.path.exists(path):
        raise EpicManagerError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Basic validation
    for req in ("title", "body", "children"):
        if req not in data:
            raise EpicManagerError(f"Missing required config key: {req}")
    if not isinstance(data.get("children"), list) or not data["children"]:
        raise EpicManagerError("Config 'children' must be a non-empty list")
    return data


def get_or_create_label(
    repo: Any,
    name: str,
    color: str = "ededed",
    description: Optional[str] = None,
    dry_run: bool = False,
) -> Any:
    """Return a Label object; create if missing.

    The repo object is expected to implement:
    - get_labels(): iterable of Label objects with .name
    - create_label(name, color, description)
    """
    logging.debug("Ensuring label exists: %s", name)
    try:
        for lbl in repo.get_labels():
            if lbl.name.lower() == name.lower():
                return lbl
    except Exception as exc:  # pragma: no cover - network/permission failure
        raise EpicManagerError(f"Unable to list labels: {exc}")

    if dry_run:
        logging.info("[dry-run] Would create label: %s", name)

        class _FakeLabel:
            def __init__(self, name: str):
                self.name = name
        return _FakeLabel(name)

    try:
        return repo.create_label(name=name, color=color, description=(description or ""))
    except Exception as exc:  # pragma: no cover - network/permission failure
        raise EpicManagerError(f"Unable to create label '{name}': {exc}")


def find_issue_by_title(repo: Any, title: str) -> Optional[Any]:
    """Find an issue by exact title (case-sensitive) across all states.

    Uses repo.get_issues(state='all')."""
    logging.debug("Searching for issue by title: %s", title)
    try:
        # PaginatedList supports iteration
        for issue in repo.get_issues(state="all"):
            if getattr(issue, "title", None) == title:
                return issue
        return None
    except Exception as exc:  # pragma: no cover - network/permission failure
        raise EpicManagerError(f"Unable to search issues: {exc}")


def create_issue(repo: Any, title: str, body: str, labels: List[Any], dry_run: bool = False) -> Any:
    """Create an issue. Ensure labels passed are acceptable by the repo API.

    Repo is expected to implement create_issue(title, body, labels).
    """
    if dry_run:
        logging.info("[dry-run] Would create issue: %s", title)

        class _FakeIssue:
            def __init__(self, title: str, body: str, labels: List[Any]):
                self.title = title
                self.body = body
                self.labels = labels
                self.number = -1
                self._comments = []

            def get_comments(self):
                return list(self._comments)

            def create_comment(self, body: str):
                self._comments.append(type("C", (), {"body": body}))
                return self._comments[-1]

            def edit(self, body: Optional[str] = None):
                if body is not None:
                    self.body = body
        return _FakeIssue(title, body, labels)

    try:
        return repo.create_issue(title=title, body=body, labels=labels)
    except Exception as exc:  # pragma: no cover - network/permission failure
        raise EpicManagerError(f"Unable to create issue '{title}': {exc}")


def ensure_issue(repo: Any, title: str, body: str, labels: List[Any], dry_run: bool = False) -> Any:
    """Find existing issue by title or create a new one."""
    existing = find_issue_by_title(repo, title)
    if existing:
        logging.debug("Found existing issue: %s (#%s)", title, getattr(existing, "number", "?"))
        return existing
    return create_issue(repo, title, body, labels, dry_run=dry_run)


def build_checklist(repo_full_name: str, epic_title: str, child_issues: List[Tuple[str, Any]]) -> str:
    """Build a standardized, updatable checklist for the epic comment.

    child_issues: list of (child_title, issue_obj)
    Uses GitHub markdown task list with direct issue references ("- [ ] #123").
    The section is wrapped in markers for idempotent updates.
    """
    lines = [
        MARKER_START,
        f"Epic: {epic_title}",
        "",
        "Progress:",
    ]
    for title, issue in child_issues:
        number = getattr(issue, "number", None)
        if number is not None and number != -1:
            lines.append(f"- [ ] #{number} — {title}")
        else:
            # Fallback if dry-run or missing number
            lines.append(f"- [ ] {title}")
    lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def upsert_epic_children_comment(epic_issue: Any, checklist_body: str) -> None:
    """Create or update the managed checklist comment on the epic.

    Searches existing comments for our marker and edits; otherwise creates a new one.
    """
    try:
        comments = list(epic_issue.get_comments())
    except Exception as exc:  # pragma: no cover
        raise EpicManagerError(f"Unable to get comments for epic: {exc}")

    # Find existing managed comment
    managed = None
    for c in comments:
        body = getattr(c, "body", "")
        if MARKER_START in body and MARKER_END in body:
            managed = c
            break
    if managed is None:
        epic_issue.create_comment(checklist_body)
        logging.info("Added checklist comment to epic #%s", getattr(epic_issue, "number", "?"))
    else:
        # PyGithub Comment has .edit(body)
        if hasattr(managed, "edit"):
            managed.edit(checklist_body)
        else:
            # Fallback: append a new one
            epic_issue.create_comment(checklist_body)
        logging.info("Updated checklist comment on epic #%s", getattr(epic_issue, "number", "?"))


def link_child_to_epic(child_issue: Any, epic_issue: Any) -> None:
    """Post a backlink comment on a child issue pointing to the epic."""
    epic_num = getattr(epic_issue, "number", None)
    if epic_num is None:
        return
    backlink = f"Linked to Epic: #{epic_num}"
    try:
        for c in child_issue.get_comments():
            if backlink in getattr(c, "body", ""):
                return  # already linked
        child_issue.create_comment(backlink)
    except Exception as exc:  # pragma: no cover
        raise EpicManagerError(f"Unable to link child issue to epic: {exc}")


def ensure_labels(repo: Any, labels: List[str], dry_run: bool = False) -> List[Any]:
    """Ensure all labels exist and return label objects list."""
    label_objs: List[Any] = []
    for name in labels:
        # Use a deterministic default color for known labels
        color = {
            "epic": "5319e7",
            "feature": "a2eeef",
            "bug": "d73a4a",
            "docs": "0075ca",
            "task": "cfd3d7",
            "map": "bfd4f2",
            "fov": "fef2c0",
            "ui": "c5def5",
            "perf": "ffccd7",
            "accessibility": "0e8a16",
            "save": "d4c5f9",
        }.get(name.lower(), "ededed")
        label_objs.append(
            get_or_create_label(repo, name, color=color, dry_run=dry_run)
        )
    return label_objs


def process_epic(repo: Any, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Create/update an Epic and its child issues based on config.

    Returns a summary dict with epic_number and children mapping.
    """
    epic_title = config["title"].strip()
    epic_body = config.get("body", "").strip()
    epic_labels_cfg = config.get("labels", ["epic"])

    # Ensure labels and create/get epic
    epic_label_objs = ensure_labels(
        repo,
        list(set(epic_labels_cfg + ["epic"])),
        dry_run=dry_run,
    )
    epic_issue = ensure_issue(repo, epic_title, epic_body, epic_label_objs, dry_run=dry_run)

    # Children
    children_defs: List[Dict[str, Any]] = config["children"]
    child_issues: List[Tuple[str, Any]] = []
    all_child_numbers: List[int] = []

    for child in children_defs:
        title = child["title"].strip()
        body = child.get("body", "").strip()
        child_labels_cfg = child.get("labels", ["feature"]) or ["feature"]
        child_label_objs = ensure_labels(
            repo,
            child_labels_cfg,
            dry_run=dry_run,
        )
        issue = ensure_issue(repo, title, body, child_label_objs, dry_run=dry_run)
        child_issues.append((title, issue))
        if getattr(issue, "number", None) is not None and getattr(issue, "number") != -1:
            all_child_numbers.append(issue.number)
        # Backlink child -> epic
        link_child_to_epic(issue, epic_issue)

    # Create/update checklist on epic
    checklist_body = build_checklist(
        getattr(repo, "full_name", ""),
        epic_title,
        child_issues,
    )
    upsert_epic_children_comment(epic_issue, checklist_body)

    logging.info(
        "Epic processed: #%s with %d children",
        getattr(epic_issue, "number", "?"),
        len(child_issues),
    )

    return {
        "epic_number": getattr(epic_issue, "number", None),
        "child_numbers": all_child_numbers,
    }


def connect_repo(repo_full_name: str, token: Optional[str]) -> Any:  # pragma: no cover - network
    if Github is None:
        raise EpicManagerError("PyGithub is not installed. Add 'PyGithub' to your dependencies.")
    if not token:
        raise EpicManagerError("A GitHub token is required. Set GITHUB_TOKEN or pass --token.")
    gh = Github(token)
    try:
        return gh.get_repo(repo_full_name)
    except GithubException as exc:
        raise EpicManagerError(f"Unable to access repo '{repo_full_name}': {exc}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:  # pragma: no cover - thin wrapper
    parser = argparse.ArgumentParser(
        description="Create/Update an Epic and its child issues from YAML config."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repo in 'owner/name' format",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to epic YAML configuration",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (or set GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call GitHub; simulate actions",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:  # pragma: no cover - CLI wrapper
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )

    try:
        cfg = load_config(args.config)
        if args.dry_run:
            # Dry-run uses a minimal fake repo object compatible with our API
            logging.info("Running in dry-run mode. No changes will be made.")

            class _FakeLabel:
                def __init__(self, name: str):
                    self.name = name

            class _FakeComment:
                def __init__(self, body: str):
                    self.body = body

                def edit(self, body: str):
                    self.body = body

            class _FakeIssue:
                _counter = 1000

                def __init__(self, title: str, body: str, labels: List[_FakeLabel]):
                    _FakeIssue._counter += 1
                    self.title = title
                    self.body = body
                    self.labels = labels
                    self.number = _FakeIssue._counter
                    self._comments: List[_FakeComment] = []

                def get_comments(self):
                    return list(self._comments)

                def create_comment(self, body: str):
                    c = _FakeComment(body)
                    self._comments.append(c)
                    return c

                def edit(self, body: Optional[str] = None):
                    if body is not None:
                        self.body = body

            class _FakeRepo:
                def __init__(self):
                    self.full_name = args.repo
                    self._labels: Dict[str, _FakeLabel] = {}
                    self._issues: List[_FakeIssue] = []

                def get_labels(self):
                    return list(self._labels.values())

                def create_label(self, name: str, color: str, description: str):
                    lbl = _FakeLabel(name)
                    self._labels[name.lower()] = lbl
                    return lbl

                def get_issues(self, state: str = "open"):
                    return list(self._issues)

                def create_issue(
                    self,
                    title: str,
                    body: str,
                    labels: List[_FakeLabel],
                ):
                    issue = _FakeIssue(title, body, labels)
                    self._issues.append(issue)
                    return issue

            repo = _FakeRepo()
        else:
            repo = connect_repo(args.repo, args.token)
        summary = process_epic(repo, cfg, dry_run=args.dry_run)
        logging.info(
            "Done. Epic: %s Children: %s",
            summary.get("epic_number"),
            summary.get("child_numbers"),
        )
        return 0
    except EpicManagerError as exc:
        logging.error(str(exc))
        return 2
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)
        return 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
