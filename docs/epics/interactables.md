# EPIC: Interactables (Chests, Traps, Doors)

Summary
- Chests with variable quality, traps, keys & doors.
- Goal: Track and group related child issues under this Epic.
- Target Window: 2025-08-26 → (Ongoing)

How to create the Epic and child issues
1. Ensure you have a GitHub personal access token with repo scope.
2. Export it: export GITHUB_TOKEN=ghp_yourtoken
3. Run the tool against your repo:
   python tools/epic_manager.py --repo your-org/amor-mortuorum --config configs/epics/interactables.yml

What the tool does
- Ensures the epic label exists.
- Creates or updates all child issues from the config, applying labels.
- Creates or updates the Epic issue with a managed checklist of child links.
- Comments on each child issue with a link back to the Epic.
- Idempotent: re-running updates bodies and labels without duplicating issues.

Managed block
The epic issue will contain a managed block to keep the checklist up to date:
<!-- epic-manager:start -->
Linked Issues
- [ ] [Feature: Chest system MVP](...)
- [ ] [Feature: Trap system MVP](...)
...
<!-- epic-manager:end -->

Troubleshooting
- Missing token: provide via --token or GITHUB_TOKEN env.
- Repo format: must be owner/name.
- Dry run: use --dry-run to preview actions without API calls.
