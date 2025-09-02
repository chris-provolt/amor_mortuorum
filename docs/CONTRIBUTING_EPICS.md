Managing Epics and Child Issues

Overview
This repository uses an Epic workflow to coordinate multi-issue bodies of work (e.g., Bosses & Balance). An Epic issue holds the summary and a checklist of linked child issues.

Workflow
1) Create/Update Epic YAML
- Define or update configs/epics/bosses_balance.yaml with the epic meta and child issues.

2) Generate Issues (Dry Run)
- python tools/epics/generate_github_issues.py --config configs/epics/bosses_balance.yaml --dry-run --output-dir .artifacts/issues
- This produces markdown files for child issues and a checklist at docs/epics/checklists/EPIC_Bosses_Balance_checklist.md.

3) Create GitHub Issues (Optional Live)
- export GH_TOKEN=your_token
- python tools/epics/generate_github_issues.py --config configs/epics/bosses_balance.yaml --repo <owner>/<repo>
- Paste the generated checklist into a comment on the Epic issue.

Best Practices
- Keep acceptance criteria specific and testable.
- Apply consistent labels from YAML to ease tracking and filters.
- Link dependencies in issue bodies as they become known.
- Update the Epic checklist as issues are created/closed.

FAQ
- Why YAML? Repeatability and single-source-of-truth for planning.
- Can I add more children mid-epic? Yes; update YAML and regenerate in dry-run to refresh the checklist and new issue markdowns.
