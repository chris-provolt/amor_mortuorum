# EPIC: Bosses & Balance

Summary
Amor Mortuorum features minibosses on floors 20/40/60/80 and a Final Boss on B99. This epic groups all design, implementation, data, and balance work required to deliver these encounters, their drops, and tuning curves.

Goal
- Track and coordinate all child issues related to bosses, loot drops, and balance curves.
- Provide a single place to monitor progress.

Target Window
- Start: 2025-08-26
- Ongoing

Acceptance Criteria
- Child issues exist and are linked in comments on the Epic issue.
- Label epic is applied to the Epic issue.
- Progress can be tracked via a linked issues checklist.

How to Use This Epic
- Create this Epic issue using the .github/ISSUE_TEMPLATE/epic.md template (or convert an existing issue by adding the epic label).
- Use the provided YAML in configs/epics/bosses_balance.yaml and the generator tool to create all child issues with consistent bodies and labels.
- Paste the generated checklist (docs/epics/checklists/EPIC_Bosses_Balance_checklist.md) as a comment on the Epic issue to track progress.

Key Scope Areas
- Minibosses on floors 20/40/60/80
- Final Boss at B99
- Boss gates, floor triggers, and encounter scheduling
- Boss AI, phases, skills, and turn-based integration
- Loot tables, unique boss drops, and economy balance
- Depth-scaling curves for enemies, chests, and portal spawn chance
- Telemetry hooks and regression tests for balance

Child Issues (Planned)
Note: The authoritative list is defined in configs/epics/bosses_balance.yaml and generated into a paste-ready checklist at docs/epics/checklists/EPIC_Bosses_Balance_checklist.md.

- [ ] Design: Minibosses floors 20/40/60/80
- [ ] Feature: Boss gate and floor triggers
- [ ] Feature: Miniboss encounter generator and scheduling
- [ ] Feature: Final Boss (B99) encounter design & integration
- [ ] Feature: Boss AI, phases, and skills
- [ ] Data: Loot tables and boss unique drops
- [ ] Balance: Enemy stat curves by depth
- [ ] Balance: Chest quality and item economy curve
- [ ] Feature: Portal spawn chance curve config and tests
- [ ] Feature: Telemetry hooks and balance dashboards
- [ ] QA: Boss and balance regression test suite
- [ ] Docs: Bosses & Balance design document and tuning playbook

Referencing This Epic From Child Issues
Include in each child issue body:
- Epic: link to this Epic issue
- Dependencies: other related issues if applicable
- Acceptance Criteria: measurable completion definition

Automation Support
- Tools
  - tools/epics/generate_github_issues.py reads configs/epics/bosses_balance.yaml and generates child issue markdown and a checklist.
- Usage (dry-run)
  - python tools/epics/generate_github_issues.py --config configs/epics/bosses_balance.yaml --epic-doc docs/epics/EPIC_Bosses_Balance.md --dry-run --output-dir .artifacts/issues
- Usage (GitHub API; optional)
  - Requires GH_TOKEN and --repo owner/name. The script will operate in dry-run mode if these are not provided.

Notes
- This Epic is ongoing; balance is iterative. Maintain telemetry and test coverage to support continuous tuning.
