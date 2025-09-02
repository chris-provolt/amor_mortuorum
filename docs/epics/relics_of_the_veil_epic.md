# EPIC: Relics of the Veil (Meta)

Summary
Relics data, acquisition logic, final relic, passive toggles.

Goal: Track and group related child issues under this Epic.
Target Window: 2025-08-26 → (Ongoing)

How to apply/update this Epic via CLI
- Ensure you have a GitHub Personal Access Token (PAT) with repo scope in env var GITHUB_TOKEN
- Run:
  python -m src.epics.cli --repo owner/repo --config configs/epics/relics_of_the_veil.yaml --json

What this does
- Ensures the epic label exists
- Creates or reuses the Epic issue by title
- Creates or reuses child issues by title
- Adds a checklist of child issues to the Epic body with open/closed state
- Adds comments to child issues linking back to the Epic

Notes
- The script is idempotent. Re-running it will reuse existing issues with the same titles.
- You can extend the YAML with more child issues as the epic evolves. Re-run to update the checklist.
