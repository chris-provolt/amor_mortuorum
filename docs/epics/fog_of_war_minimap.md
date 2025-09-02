# EPIC: Fog of War & Minimap

Summary
- Implement visibility (FOV), explored tiles, and the minimap with toggle & icons.
- This document describes the scope and provides operator instructions to create the GitHub Epic with child issues.

Why an Epic?
- Groups multiple cross-cutting tasks (engine, UI, save system, accessibility, performance) under a single tracker.

How to create/update the Epic and children
1) Ensure you have a GitHub Personal Access Token with repo scope.
   - export GITHUB_TOKEN=ghp_yourtoken
2) Dry-run (no network calls):
   - python tools/epics/epic_manager.py --repo OWNER/REPO --config tools/epics/configs/fog_of_war_minimap.yml --dry-run --log-level DEBUG
3) Create/update for real:
   - python tools/epics/epic_manager.py --repo OWNER/REPO --config tools/epics/configs/fog_of_war_minimap.yml --log-level INFO

What the script does
- Ensures the 'epic' label exists.
- Creates the Epic issue titled "EPIC: Fog of War & Minimap" if it does not exist; otherwise reuses it.
- Creates child issues as defined in the YAML config (if missing).
- Posts/updates a managed checklist comment on the Epic with links to child issues.
- Comments on each child issue with a backlink to the Epic.

Acceptance alignment
- Child issues exist and are linked in comments: auto-created and mutually linked.
- Labels applied: 'epic': enforced on the Epic issue.
- Progress tracked via linked issues checklist: the Epic receives an updatable task list with #issue links.

Note
- Re-running the script is idempotent. It updates the checklist comment instead of duplicating it, and will not recreate issues with the same title.
