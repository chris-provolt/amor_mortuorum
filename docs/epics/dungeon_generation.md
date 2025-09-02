# EPIC: Dungeon Generation & Navigation

This Epic tracks the procedural map generation and movement/rendering stack: BSP rooms, cellular caverns, stairs placement, tile rendering, pathfinding, and minimap.

How to create the Epic and child issues automatically in this repository:

- Ensure you have a Personal Access Token (classic) with repo scope or rely on GITHUB_TOKEN in CI.
- Run the CLI locally:
  - python -m am_epic.cli apply -c configs/epics/dungeon_generation.yml --repo OWNER/REPO --token $GITHUB_TOKEN
- Or trigger the provided GitHub Action workflow "Manage Epics" with the same config.

What this does:
- Ensures label "epic" and "epic-child" exist
- Creates/updates an Epic issue titled "EPIC: Dungeon Generation & Navigation"
- Creates/updates child issues for each task
- Adds a dynamic checklist to the Epic body showing progress of child issues
- Comments on the Epic with a list of children and on each child with a link back to the Epic

Re-running the command is safe; it is idempotent and updates the checklist and comments.
