Epic tracking and automation

Purpose
- Provide a consistent way to author Epics and keep their linked child issues and progress checklist up to date.

What this provides
- YAML-based Epic definition (title, body, labels, and child issues)
- Scripted synchronization using GitHub REST API
- GitHub Action to sync on-demand and when Epic issues change
- Idempotent comments and body sections for clean updates

Files
- configs/epics/*.yaml: Epic definitions. Example: configs/epics/audio_atmosphere.yaml
- tools/epics/sync_epic.py: CLI to run synchronization
- src/epics/manager.py: Core logic to render/update issues
- src/epics/github_api.py: Minimal GitHub API wrapper
- .github/workflows/epic_sync.yml: CI workflow to run the sync
- .github/ISSUE_TEMPLATE/epic.yml: Template to open Epics with correct label

How to use
1) Author or edit a config under configs/epics, e.g., configs/epics/audio_atmosphere.yaml.
2) Run locally:
   - export GITHUB_TOKEN=ghp_your_pat
   - export GITHUB_REPOSITORY=owner/repo
   - python tools/epics/sync_epic.py --config configs/epics/audio_atmosphere.yaml
3) Or run via GitHub Action:
   - Actions → Epic Sync → Run workflow → set config_path to the YAML.
4) Once created, you can also let the Action maintain the Epic when it changes:
   - Any time an issue with label "epic" is opened/edited/labeled, the workflow will try to infer the matching config by title and synchronize.

Conventions
- The Epic body contains a Progress section that is replaced between markers:
  <!-- epic-checklist:start --> ... <!-- epic-checklist:end -->
- A dedicated comment on the Epic lists child issues between markers:
  <!-- epic-child-links:start --> ... <!-- epic-child-links:end -->
- Each child has a link-back comment with markers:
  <!-- linked-to-epic:start --> Linked to Epic #N <!-- linked-to-epic:end -->

Notes
- The sync is idempotent. Running multiple times will not duplicate comments.
- The tool searches for issues by exact title. Renaming issues may break linkage; update the config or rename back.
- Labels are ensured automatically. If creation fails due to permissions, the sync continues best-effort.

Testing
- Unit tests mock the GitHub API to verify checklist generation, idempotency, and linkage behavior.
