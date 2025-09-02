# Save System Design

Overview
The save system is split into two layers:
- Meta State (persistent across runs): Relics and Crypt
- Run State (current run): Floor, in_graveyard flag, RNG seed, timestamps

Schema
- JSON format with a top-level SaveGame object containing meta and optional run
- schema_version allows forward-compatible migrations

Files and Atomicity
- meta.json and run.json per profile under platform-specific save root
- Atomic writes: write .tmp, fsync, move to .bak, rename .tmp -> real file
- Recovery: on load, attempt primary, then .bak, then the other file as last resort

Policies
- Meta saves: always allowed
- Full saves: allowed only when run.in_graveyard is True
- Save-and-quit: off by default; can be enabled via SavePolicy

Extensibility
- Migrations scaffold provided in codec.migrate_data
- Additional meta fields can be added without breaking schema
- Encryption/obfuscation can be layered on encode/decode later

Testing
- tests/test_persistence.py covers capacity limits, validation, policy enforcement, and recovery
