# EPIC: Loot, Items & Economy

Summary
Item schema, equip/unequip, consumables, resurrection token, gold/economy.

Goal: Track and group related child issues under this Epic.
Target Window: 2025-08-26 → (Ongoing)

Acceptance
- Child issues exist and are linked in comments.
- Labels applied: epic.
- Progress can be tracked via linked issues checklist.

How to use
1) Ensure you have a GitHub Personal Access Token (classic) with repo scope set in env:
   export GITHUB_TOKEN=ghp_...
2) Review and adjust the child issues in configs/epics/loot_items_economy.yml
3) Run the Epic manager to create/update the Epic and children in your repository:
   python -m src.pm.epic_manager <owner>/<repo> configs/epics/loot_items_economy.yml

What this does
- Creates (or finds) the Epic issue with label epic
- Creates (or finds) each child issue with label epic-child and any additional labels defined
- Updates the Epic body with a checklist of linked issues
- Adds a comment to the Epic listing all child issues

Notes
- Re-running the command is idempotent based on exact title matching.
- You can add more child issues to the YAML and re-run to extend the Epic.
- Consider adding additional labels like balance, ui, items to support filtering.
