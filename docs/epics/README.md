Epic Management Utilities

This folder contains documentation and configuration for managing GitHub Epics and their child issues programmatically.

- fog_of_war_minimap.md: Narrative description and operator guide for the Fog of War & Minimap epic.
- ../.. /tools/epics/configs/fog_of_war_minimap.yml: The source of truth for the epic and child issues.
- Use tools/epics/epic_manager.py to create/update the Epic and child issues.

Quickstart
- Ensure Python 3.9+ and install dependencies: PyYAML and PyGithub (if not using dry-run).
- export GITHUB_TOKEN=yourtoken
- python tools/epics/epic_manager.py --repo OWNER/REPO --config tools/epics/configs/fog_of_war_minimap.yml
