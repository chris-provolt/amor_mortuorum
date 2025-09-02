---
name: Feature - Save System / Persistence
about: Implement or extend save system functionality
title: "Persistence: <Component>"
labels: [feature, persistence]
assignees: []
---

## Problem
Describe the problem or behavior to implement.

## Proposal
- [ ] Data model changes
- [ ] Encoding/Decoding changes
- [ ] Manager behavior changes
- [ ] Error handling & validation
- [ ] Tests
- [ ] Docs

## Acceptance Criteria
- Unit tests cover success and failure paths
- Docs updated under docs/epics/save_system.md
- No regressions to existing save functionality

## Notes
- Respect Graveyard-only policy for full saves
- SCHEMA_VERSION must be bumped if breaking changes are introduced
