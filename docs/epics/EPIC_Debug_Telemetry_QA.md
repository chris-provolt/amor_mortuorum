# EPIC: Debugging, Telemetry & QA

Summary
- Implement developer-facing debugging tools, structured telemetry, and QA determinism harness.
- Goal: Improve observability, reproducibility, and testability across the game.
- Target Window: 2025-08-26 → Ongoing

Acceptance
- Child issues exist and are linked in comments.
- Label applied: epic.
- Progress can be tracked via linked issues checklist.

Linked Issues (create these and link back to this Epic)
- [ ] #TODO Create: Debug Overlay (UI, toggles, perf/memory, seed) — link issue URL here
- [ ] #TODO Create: Seed Controls & Determinism (global RNG policy) — link issue URL here
- [ ] #TODO Create: Telemetry Client (JSONL to disk, rotation, context) — link issue URL here
- [ ] #TODO Create: QA Harness (record/replay RNG ops) — link issue URL here
- [ ] #TODO Create: Integration with Game Loop (Arcade bindings, input to toggle overlay)
- [ ] #TODO Create: Unit & Integration Tests for tools above
- [ ] #TODO Create: Documentation (README sections, developer guide)

Notes
- This Epic provides scaffolding in src/amor and tests/*.
- Overlay is framework-agnostic and will render via Arcade when available.
- Telemetry is offline-first; no PII; JSON-Lines to .amor/telemetry by default.
- QA harness ensures content generation reproducibility; critical for 99-floor dungeon test plans.
