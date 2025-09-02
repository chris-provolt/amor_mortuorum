# EPIC: Graveyard (Hub)

Summary
- Implemented headless Graveyard hub domain: rest, limited-stock shop, and 3-slot crypt with persistence.
- Deterministic shop restock per hub cycle using meta seed in save.
- Atomic JSON save system with versioning.

How it maps to README
- Graveyard hub: rest (heal) is available via GraveyardHub.rest.
- Shop with limited stock: Shop.restock limits quantities per cycle, purchase drains stock.
- Crypt stores up to 3 items persistently between runs; integrated with SaveManager.

Testing & Determinism
- Pytest unit tests cover rest, shop stock limits, crypt capacity and persistence, atomic saves.
- Shop restock uses seed ^ cycle to keep deterministic results across reloads.

Integration
- UI layers (Arcade or CLI) can compose these services without modification.
- Save files stored under ~/.amor_mortuorum/saves/meta.json by default; tests pass a temp root.
