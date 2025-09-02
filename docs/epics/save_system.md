# EPIC: Save System & Persistence

Summary
- Implement robust save system for meta progression (Relics of the Veil and Crypt), graveyard-only full saving, and lay groundwork for later save-and-quit.
- Track progress via linked child issues.

Labels
- epic

Goals
- Meta saves (crypt/relics) persist across runs
- Graveyard-only full saving by default
- Save-and-quit capability as a feature flag later
- Deterministic, versioned, atomic, recoverable persistence layer

Acceptance
- Child issues exist and are linked in comments
- Label applied: epic
- Progress tracked via linked issues checklist below

Linked Issues (Checklist)
- [ ] Meta State persistence (Relics + Crypt)
- [ ] SaveManager with atomic I/O and backups
- [ ] Graveyard-only full save enforcement
- [ ] Save-and-quit feature flag implementation
- [ ] Corruption handling and recovery strategy
- [ ] Save schema versioning and migration scaffolding
- [ ] Save directory structure and profile management
- [ ] Documentation for save system
- [ ] Unit tests for persistence edge cases

How to Use
1. Create GitHub issues for each checklist item above.
2. Link them in this Epic via comments using GitHub's issue linking (e.g., `#123`).
3. Apply the `epic` label to this issue.
4. Use the checklist to track progress.

Architecture Highlights
- JSON, human-readable save files with schema_version
- Atomic writes with .tmp + .bak backup file strategy
- Separate files: meta.json (always safe to write) and run.json (mirrors full save)
- Run saves only allowed at Graveyard unless save-and-quit is enabled
- Platform-specific save folder under a per-profile directory

File Layout (per profile)
- profiles/<profile_id>/meta.json
- profiles/<profile_id>/meta.json.bak
- profiles/<profile_id>/run.json
- profiles/<profile_id>/run.json.bak

Future Work
- Encryption/obfuscation for anti-tamper if desired
- Cloud sync hooks
- Multiple save slots / profiles UI
- Snapshotting with rolling backups
