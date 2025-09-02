Epic management automation

This repo contains a small tool to create and maintain GitHub Epic issues and child issues from a YAML spec.

Quick start:
- Install dependencies: pip install -e . requests pyyaml
- Create or edit your epic spec under configs/epics/
- Run: python -m am_epic.cli apply -c configs/epics/dungeon_generation.yml --repo OWNER/REPO --token $GITHUB_TOKEN

Behavior:
- Ensures labels 'epic' and 'epic-child' exist
- Upserts the Epic and child issues by title
- Links child issues with comments
- Adds a generated checklist to the Epic body between markers; safe to re-run

CI:
- Use the included GitHub Actions workflow Manage Epics (workflow_dispatch) to apply specs with the built-in GITHUB_TOKEN.
