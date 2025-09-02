Amor Mortuorum: Platform-appropriate directories and migration

Overview
- Uses platformdirs to resolve OS-correct folders for config, saves (user data), logs, and cache.
- Supports environment overrides for testing and power users:
  - AMOR_CONFIG_DIR, AMOR_SAVE_DIR, AMOR_LOG_DIR, AMOR_CACHE_DIR
- Migrates content from repository scaffolding directories if present:
  - ./configs -> user_config_dir
  - ./data/saves or ./saves -> user_data_dir/saves

Locations by platform (via platformdirs)
- Windows:
  - Config: %APPDATA%/Amor Mortuorum
  - Saves: %LOCALAPPDATA%/Amor Mortuorum/saves
  - Logs: %LOCALAPPDATA%/Amor Mortuorum/logs
  - Cache: %LOCALAPPDATA%/Amor Mortuorum/Cache
- macOS:
  - Config: ~/Library/Application Support/Amor Mortuorum
  - Saves: ~/Library/Application Support/Amor Mortuorum/saves
  - Logs: ~/Library/Logs/Amor Mortuorum (or within Application Support depending on platformdirs)
  - Cache: ~/Library/Caches/Amor Mortuorum
- Linux/BSD:
  - Config: ~/.config/Amor Mortuorum
  - Saves: ~/.local/share/Amor Mortuorum/saves
  - Logs: ~/.local/state/Amor Mortuorum/logs (if available) or ~/.local/share/Amor Mortuorum/logs
  - Cache: ~/.cache/Amor Mortuorum

Migration behavior
- If destination does not exist, files/directories are moved as-is.
- If destination exists:
  - Directory vs directory: recursively merge.
  - File vs file: if identical, the source is dropped; if different, the source is preserved with a .migrated timestamp and placed next to the destination.
- Empty scaffolding directories are pruned.
- A .migration.log is appended in the destination to record actions.

Usage
- Call initialize_app_paths() early during application startup. It ensures directories then migrates any scaffolding contents.
- For deterministic tests, set environment overrides to temporary directories.
