Issue Sync Tool (Epics and Child Issues)

This repository includes a small utility to create and maintain GitHub Epics (as Issues) and their child issues.

Why: Some teams prefer to manage Epics via Issues. This tool ensures child issues exist, are labeled, and are linked in a managed checklist comment on the Epic.

How it works:
- Define an Epic and children in a YAML file (see configs/issues/epics/ui_hud.yml)
- Run the sync tool locally or via CI
- The tool creates/updates the Epic + child issues and posts a managed comment with a live checklist

Usage:
1) Prepare environment variables:
   - GITHUB_TOKEN: Personal Access Token (repo scope) or GitHub Actions token
   - GITHUB_REPOSITORY: owner/repo slug

2) Dry-run (no changes):
   python tools/issue_sync.py --config configs/issues/epics/ui_hud.yml

3) Apply changes:
   python tools/issue_sync.py --config configs/issues/epics/ui_hud.yml --apply

Notes:
- Idempotent: Matching is by exact title; bodies include a hidden marker for tracking.
- Labels: Missing labels are created automatically with default colors.
- Checklist: The epic comment is rewritten each run to reflect current open/closed states.

Extending:
- Duplicate the YAML for new epics and adjust titles/children.
- Add labels to LABEL_COLORS in tools/issue_sync.py for custom colors.

CI Integration (example):
- Add a GitHub Actions workflow that runs the tool on push to main:

  name: Sync Issues (UI/HUD Epic)
  on:
    push:
      branches: [ main ]
      paths:
        - configs/issues/epics/ui_hud.yml
        - tools/issue_sync.py
  jobs:
    sync:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - run: pip install requests pyyaml
        - env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
            GITHUB_REPOSITORY: ${{ github.repository }}
          run: python tools/issue_sync.py --config configs/issues/epics/ui_hud.yml --apply
