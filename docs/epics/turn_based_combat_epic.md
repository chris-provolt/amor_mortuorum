# EPIC: Turn-Based Combat (FF1-style)

Summary
Combat UI, turn queue, commands, items, defend, flee, log.

Goal: Track and group related child issues under this Epic.
Target Window: 2025-08-26 → (Ongoing)

Why this matters
- Core to the gameplay loop: exploration leads to deterministic, tactical combat.
- Enables balancing, itemization, and accessibility across the experience.

Acceptance
- Child issues exist and are linked in comments.
- Labels applied: epic.
- Progress can be tracked via linked issues checklist.

How to create issues
- Ensure you have a GitHub token with repo scope in GITHUB_TOKEN.
- Ensure GITHUB_REPO is set to owner/repo.
- Run the generator:
  - Dry run: python tools/create_epic_and_issues.py --config configs/epics/turn_based_combat.yaml --dry-run --repo "$GITHUB_REPO"
  - Apply:   python tools/create_epic_and_issues.py --config configs/epics/turn_based_combat.yaml --repo "$GITHUB_REPO" --token "$GITHUB_TOKEN"

What the tool does
- Ensures the epic label exists.
- Creates child issues if not already present by exact title.
- Creates the epic with a checklist that links to the child issues (#NN).
- Adds a comment on each child pointing to the parent epic, and a summary comment on the epic listing all children.

Child work breakdown
- See configs/epics/turn_based_combat.yaml for authoritative list and acceptance criteria per child.
